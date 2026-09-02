"""Calendar time context for RAG chat."""

from __future__ import annotations

from datetime import datetime, timezone

from core.proactive.detector import upcoming_events


def calendar_context_block(minutes_ahead: int = 240) -> str:
    """
    Return a short text block describing upcoming calendar events for LLM context.
    Empty string when calendar is not connected or no events.
    """
    events = upcoming_events(minutes_ahead=minutes_ahead)
    if not events:
        return ""

    lines: list[str] = []
    now = datetime.now(timezone.utc)
    for event in events[:8]:
        title = event.get("summary") or event.get("title") or "(untitled)"
        start = event.get("start", {})
        when = start.get("dateTime") or start.get("date") or ""
        lines.append(f"- {title} ({when})")

    header = f"Upcoming calendar (next {minutes_ahead // 60}h, as of {now.strftime('%Y-%m-%d %H:%M UTC')}):"
    return header + "\n" + "\n".join(lines)
