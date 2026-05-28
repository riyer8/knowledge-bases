from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from core.config import config
from core.memory.graph import load_graph, get_person_events
from core.privacy.hasher import resolve_hash


def pending_emails() -> list[dict]:
    """Return unreplied email threads from Gmail. Empty list if Gmail not connected."""
    try:
        from core.integrations.gmail import get_pending_threads
        return get_pending_threads(days_back=7)
    except Exception:
        return []


def upcoming_events(minutes_ahead: int = 60) -> list[dict]:
    """Return GCal events starting in the next `minutes_ahead` minutes."""
    try:
        from core.integrations.gcal import sync as gcal_sync
        from core.integrations.oauth import load_token
        if not load_token("gcal"):
            return []
        # Re-use gcal module's API helper rather than duplicating it
        from core.integrations import gcal as gcal_mod
        return gcal_mod._api_get("/calendars/primary/events", params={
            "timeMin": datetime.now(timezone.utc).isoformat(),
            "timeMax": (datetime.now(timezone.utc) + timedelta(minutes=minutes_ahead)).isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "5",
        }).get("items", [])
    except Exception:
        return []


def relationship_drift(inactive_days: int = 14) -> list[dict]:
    """Return people not seen in the event log for `inactive_days` days."""
    graph = load_graph()
    cutoff = datetime.now(timezone.utc) - timedelta(days=inactive_days)
    person_nodes = {nid for nid in graph if nid.startswith("person:")}

    drifted: list[dict] = []
    for person_node in person_nodes:
        h = person_node[len("person:"):]
        event_ids = get_person_events(h)
        if not event_ids:
            continue
        last_seen: Optional[datetime] = _last_seen_date(event_ids)
        if last_seen and last_seen < cutoff:
            drifted.append({
                "person_hash": h,
                "display_name": resolve_hash(h) or h,
                "last_seen": last_seen.isoformat(),
                "days_since": (datetime.now(timezone.utc) - last_seen).days,
            })

    return sorted(drifted, key=lambda x: x["days_since"], reverse=True)


def _last_seen_date(event_ids: list[str]) -> Optional[datetime]:
    clean_dir = config.events_clean_dir
    if not clean_dir.exists():
        return None

    target_ids = set(event_ids)
    latest: Optional[datetime] = None

    for log_file in sorted(clean_dir.glob("*.jsonl"), reverse=True):
        for line in log_file.read_text().splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("id") not in target_ids:
                continue
            try:
                ts = datetime.fromisoformat(event.get("timestamp", "").replace("Z", "+00:00"))
                if latest is None or ts > latest:
                    latest = ts
            except Exception:
                continue

    return latest
