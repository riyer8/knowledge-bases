from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from core.config import config
from core.memory.graph import _load_graph, get_person_events
from core.privacy.hasher import resolve_hash


def pending_emails() -> list[dict]:
    """Return unreplied email threads from Gmail. Empty list if Gmail not connected."""
    try:
        from core.integrations.gmail import get_pending_threads
        return get_pending_threads(days_back=7)
    except RuntimeError:
        return []
    except Exception:
        return []


def upcoming_events(minutes_ahead: int = 60) -> list[dict]:
    """Return GCal events starting in the next `minutes_ahead` minutes."""
    try:
        from core.integrations.oauth import load_token, get_access_token, is_expired
        import json, urllib.request, urllib.parse
        import os

        client_id = os.environ.get("KB_GCAL_CLIENT_ID", "")
        client_secret = os.environ.get("KB_GCAL_CLIENT_SECRET", "")
        token = load_token("gcal")
        if not token:
            return []

        access_token = get_access_token("gcal", client_id, client_secret)
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(minutes=minutes_ahead)).isoformat()

        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "5",
        }
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        results = []
        for event in data.get("items", []):
            if event.get("status") == "cancelled":
                continue
            start = event.get("start", {})
            start_str = start.get("dateTime") or start.get("date", "")
            results.append({
                "title": event.get("summary", "Untitled"),
                "start": start_str,
                "html_link": event.get("htmlLink", ""),
            })
        return results
    except Exception:
        return []


def relationship_drift(inactive_days: int = 14) -> list[dict]:
    """
    Return people (hashes) not seen in the event log for `inactive_days` days.
    Uses the knowledge graph to find last interaction.
    """
    graph = _load_graph()
    cutoff = datetime.now(timezone.utc) - timedelta(days=inactive_days)

    # Find all person nodes
    person_nodes = {
        node_id for node_id in graph
        if node_id.startswith("person:")
    }

    drifted: list[dict] = []
    for person_node in person_nodes:
        h = person_node[len("person:"):]
        event_ids = get_person_events(h)
        if not event_ids:
            continue

        # Find the most recent event involving this person by scanning clean logs
        last_seen: Optional[datetime] = _last_seen_date(event_ids)
        if last_seen and last_seen < cutoff:
            display_name = resolve_hash(h) or h
            drifted.append({
                "person_hash": h,
                "display_name": display_name,
                "last_seen": last_seen.isoformat(),
                "days_since": (datetime.now(timezone.utc) - last_seen).days,
            })

    return sorted(drifted, key=lambda x: x["days_since"], reverse=True)


def _last_seen_date(event_ids: list[str]) -> Optional[datetime]:
    """Scan clean event log to find the most recent timestamp for a set of event IDs."""
    import json as _json
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
                event = _json.loads(line)
            except Exception:
                continue
            if event.get("id") not in target_ids:
                continue
            ts_str = event.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if latest is None or ts > latest:
                    latest = ts
            except Exception:
                continue

    return latest
