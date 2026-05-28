from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

from core.ingestion.pipeline import ingest_text
from core.integrations.oauth import (
    build_auth_url, exchange_code, get_access_token, save_token
)

_SERVICE = "gcal"
_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
_REDIRECT_URI = "http://127.0.0.1:8765/integrations/gcal/callback"
_API_BASE = "https://www.googleapis.com/calendar/v3"

_CLIENT_ID = os.environ.get("KB_GCAL_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("KB_GCAL_CLIENT_SECRET", "")


def auth_url() -> str:
    if not _CLIENT_ID:
        raise RuntimeError("KB_GCAL_CLIENT_ID not set — add it to .env")
    return build_auth_url(_CLIENT_ID, _SCOPES, _REDIRECT_URI, state="gcal")


def handle_callback(code: str) -> None:
    if not _CLIENT_ID or not _CLIENT_SECRET:
        raise RuntimeError("KB_GCAL_CLIENT_ID / KB_GCAL_CLIENT_SECRET not set")
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


def _event_to_text(event: dict) -> str:
    """Convert a GCal event dict into a plain-text description for ingestion."""
    parts: list[str] = []
    title = event.get("summary", "Untitled event")
    parts.append(f"Calendar event: {title}")

    start = event.get("start", {})
    end = event.get("end", {})
    start_str = start.get("dateTime") or start.get("date", "")
    end_str = end.get("dateTime") or end.get("date", "")
    if start_str:
        parts.append(f"Start: {start_str}")
    if end_str:
        parts.append(f"End: {end_str}")

    location = event.get("location", "")
    if location:
        parts.append(f"Location: {location}")

    description = event.get("description", "")
    if description:
        parts.append(f"Description: {description[:500]}")

    attendees = event.get("attendees", [])
    if attendees:
        names = [a.get("displayName") or a.get("email", "") for a in attendees[:10]]
        parts.append(f"Attendees: {', '.join(names)}")

    return "\n".join(parts)


def sync(days_back: int = 7, days_forward: int = 14) -> int:
    """
    Pull calendar events from the past `days_back` days and next `days_forward` days.
    Ingests each event through the privacy pipeline.
    Returns number of events ingested.
    """
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days_back)).isoformat()
    time_max = (now + timedelta(days=days_forward)).isoformat()

    data = _api_get("/calendars/primary/events", params={
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": "250",
    })

    count = 0
    for event in data.get("items", []):
        status = event.get("status", "")
        if status == "cancelled":
            continue

        text = _event_to_text(event)
        start = event.get("start", {})
        attendees = event.get("attendees", [])

        metadata = {
            "kind": "gcal_event",
            "event_id": event.get("id", ""),
            "calendar": "primary",
            "attendees_raw": [a.get("email", "") for a in attendees],
            "start": start.get("dateTime") or start.get("date", ""),
            "html_link": event.get("htmlLink", ""),
        }

        ingest_text(
            text=text,
            source="gcal",
            metadata=metadata,
            flagged_important=False,
        )
        count += 1

    return count
