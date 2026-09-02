from __future__ import annotations

from core.proactive.detector import pending_emails, relationship_drift, upcoming_events
from core.proactive.life_balance import life_balance_insights


def get_insights(max_insights: int = 5) -> list[dict]:
    """
    Gather proactive insights and return them ranked by urgency.
    Each insight has: type, title, body, action_label, action_url.
    """
    insights: list[dict] = []

    # 1. Upcoming meetings (highest urgency)
    for event in upcoming_events(minutes_ahead=60):
        insights.append({
            "type": "meeting",
            "title": "Meeting soon",
            "body": event["title"],
            "action_label": "Open Calendar",
            "action_url": event.get("html_link", ""),
            "urgency": 3,
        })

    # 2. Pending emails
    emails = pending_emails()
    if emails:
        count = len(emails)
        first = emails[0]
        subject = first.get("subject", "(no subject)")
        sender = first.get("from", "")
        if count == 1:
            body = f"From {sender}: \"{subject}\""
        else:
            body = f"{count} threads waiting — newest from {sender}"
        insights.append({
            "type": "email",
            "title": f"{count} unanswered {'email' if count == 1 else 'emails'}",
            "body": body,
            "action_label": "Open Chat",
            "action_url": "",
            "urgency": 2,
        })

    # 3. Relationship drift
    drifted = relationship_drift(inactive_days=14)[:3]
    for person in drifted:
        insights.append({
            "type": "relationship",
            "title": f"Haven't talked to {person['display_name']}",
            "body": f"{person['days_since']} days since last interaction",
            "action_label": "Open Chat",
            "action_url": "",
            "urgency": 1,
        })

    # 4. Life balance patterns
    for insight in life_balance_insights(days=7):
        insights.append(insight)

    # Sort by urgency descending, cap at max_insights
    insights.sort(key=lambda x: x["urgency"], reverse=True)
    return insights[:max_insights]
