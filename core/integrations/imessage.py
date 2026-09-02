"""Read-only iMessage ingestion from local macOS chat.db."""

from __future__ import annotations

import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.ingestion.pipeline import ingest_text

_CHAT_DB = Path.home() / "Library" / "Messages" / "chat.db"
_APPLE_EPOCH_OFFSET = 978307200  # seconds between 1970 and 2001-01-01


def is_available() -> bool:
    return platform.system() == "Darwin" and _CHAT_DB.exists()


def _apple_ts_to_iso(raw: int | None) -> str:
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    # chat.db stores nanoseconds since 2001-01-01 on modern macOS
    seconds = raw / 1_000_000_000 + _APPLE_EPOCH_OFFSET
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def fetch_recent(limit: int = 30) -> list[dict[str, Any]]:
    """
    Return recent iMessage thread snippets (metadata + short text preview).
    Requires Full Disk Access on macOS for chat.db.
    """
    if not is_available():
        return []

    limit = max(1, min(limit, 200))
    try:
        conn = sqlite3.connect(f"file:{_CHAT_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return []

    try:
        rows = conn.execute(
            """
            SELECT
                m.ROWID AS message_id,
                m.text,
                m.is_from_me,
                m.date,
                h.id AS handle
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.ROWID
            WHERE m.text IS NOT NULL AND length(m.text) > 0
            ORDER BY m.date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        text = str(row["text"] or "").strip()
        if not text:
            continue
        direction = "sent" if row["is_from_me"] else "received"
        handle = str(row["handle"] or "unknown")
        results.append({
            "message_id": str(row["message_id"]),
            "handle": handle,
            "direction": direction,
            "text_preview": text[:240],
            "timestamp": _apple_ts_to_iso(row["date"]),
        })
    return results


def ingest_recent(limit: int = 20) -> dict[str, Any]:
    """Ingest recent iMessages through the privacy pipeline."""
    messages = fetch_recent(limit=limit)
    ingested = 0
    for msg in messages:
        body = (
            f"iMessage {msg['direction']} ({msg['handle']}): "
            f"{msg['text_preview']}"
        )
        ingest_text(body, source="imessage", metadata={"message_id": msg["message_id"]})
        ingested += 1
    return {"ok": True, "ingested": ingested, "available": is_available()}
