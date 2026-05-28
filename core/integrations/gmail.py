from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

from core.ingestion.pipeline import ingest_text
from core.integrations.oauth import (
    build_auth_url, exchange_code, get_access_token, save_token
)

_SERVICE = "gmail"
_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_REDIRECT_URI = "http://127.0.0.1:8765/integrations/gmail/callback"
_API_BASE = "https://gmail.googleapis.com/gmail/v1"

_CLIENT_ID = os.environ.get("KB_GMAIL_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("KB_GMAIL_CLIENT_SECRET", "")

_PENDING_DAYS = 7        # look back this many days for unanswered threads
_SYNC_MAX_THREADS = 100


def auth_url() -> str:
    if not _CLIENT_ID:
        raise RuntimeError("KB_GMAIL_CLIENT_ID not set — add it to .env")
    return build_auth_url(_CLIENT_ID, _SCOPES, _REDIRECT_URI, state="gmail")


def handle_callback(code: str) -> None:
    if not _CLIENT_ID or not _CLIENT_SECRET:
        raise RuntimeError("KB_GMAIL_CLIENT_ID / KB_GMAIL_CLIENT_SECRET not set")
    token = exchange_code(code, _CLIENT_ID, _CLIENT_SECRET, _REDIRECT_URI)
    save_token(_SERVICE, token)


def _api_get(path: str, params: Optional[dict] = None) -> dict:
    access_token = get_access_token(_SERVICE, _CLIENT_ID, _CLIENT_SECRET)
    url = _API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def _header(headers: list[dict], name: str) -> str:
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return h.get("value", "")
    return ""


def _decode_body(part: dict) -> str:
    """Extract plain-text body from a message part."""
    mime = part.get("mimeType", "")
    body_data = part.get("body", {}).get("data", "")

    if mime == "text/plain" and body_data:
        try:
            return base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="ignore")
        except Exception:
            return ""

    for sub in part.get("parts", []):
        text = _decode_body(sub)
        if text:
            return text

    return ""


def _thread_to_text(thread_data: dict, include_body: bool = False) -> tuple[str, dict]:
    """
    Convert a Gmail thread into ingestion text + metadata.
    By default pulls subject + sender metadata only (not full body).
    Set include_body=True for full content (user opt-in).
    """
    messages = thread_data.get("messages", [])
    if not messages:
        return "", {}

    first = messages[0]
    last = messages[-1]
    headers = first.get("payload", {}).get("headers", [])

    subject = _header(headers, "subject") or "(no subject)"
    sender = _header(headers, "from") or ""
    date = _header(headers, "date") or ""
    snippet = first.get("snippet", "")

    # Check if any message in thread is from "me" (a sent reply)
    has_reply = any(
        "SENT" in msg.get("labelIds", []) for msg in messages[1:]
    )

    parts: list[str] = [f"Email: {subject}"]
    if sender:
        parts.append(f"From: {sender}")
    if date:
        parts.append(f"Date: {date}")
    parts.append(f"Thread length: {len(messages)} message(s)")
    parts.append(f"Replied: {'yes' if has_reply else 'no'}")

    if include_body:
        body = _decode_body(first.get("payload", {}))
        if body:
            parts.append(f"Body:\n{body[:1000]}")
    else:
        if snippet:
            # Strip HTML entities from snippet
            clean_snippet = re.sub(r"&[a-z]+;", " ", snippet)
            parts.append(f"Preview: {clean_snippet[:200]}")

    metadata = {
        "kind": "gmail_thread",
        "thread_id": thread_data.get("id", ""),
        "subject": subject,
        "from_raw": sender,
        "replied": has_reply,
        "message_count": len(messages),
    }

    return "\n".join(parts), metadata


def sync(days_back: int = 7) -> int:
    """
    Pull recent Gmail threads and ingest them through the privacy pipeline.
    Returns number of threads ingested.
    """
    after_ts = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())
    query = f"after:{after_ts} -category:promotions -category:social"

    threads_data = _api_get("/users/me/threads", params={
        "q": query,
        "maxResults": str(_SYNC_MAX_THREADS),
    })

    count = 0
    for thread_stub in threads_data.get("threads", []):
        thread_id = thread_stub.get("id", "")
        if not thread_id:
            continue

        thread_data = _api_get(f"/users/me/threads/{thread_id}", params={
            "format": "metadata",
            "metadataHeaders": "Subject,From,Date",
        })

        text, metadata = _thread_to_text(thread_data)
        if not text:
            continue

        ingest_text(
            text=text,
            source="gmail",
            metadata=metadata,
        )
        count += 1

    return count


def get_pending_threads(days_back: int = _PENDING_DAYS) -> list[dict]:
    """
    Return a list of threads that received a message but were never replied to.
    Used by the proactive bot to surface "you haven't responded to X".
    """
    after_ts = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())
    query = f"after:{after_ts} is:inbox -from:me -category:promotions"

    threads_data = _api_get("/users/me/threads", params={
        "q": query,
        "maxResults": "50",
    })

    pending: list[dict] = []
    for thread_stub in threads_data.get("threads", []):
        thread_id = thread_stub.get("id", "")
        if not thread_id:
            continue

        thread_data = _api_get(f"/users/me/threads/{thread_id}", params={
            "format": "metadata",
            "metadataHeaders": "Subject,From,Date",
        })

        messages = thread_data.get("messages", [])
        has_reply = any("SENT" in m.get("labelIds", []) for m in messages)
        if has_reply:
            continue

        first = messages[0] if messages else {}
        headers = first.get("payload", {}).get("headers", [])
        pending.append({
            "thread_id": thread_id,
            "subject": _header(headers, "subject") or "(no subject)",
            "from": _header(headers, "from"),
            "date": _header(headers, "date"),
            "message_count": len(messages),
        })

    return pending
