"""Life balance pattern detection from bucket summaries."""

from __future__ import annotations

from core.memory.buckets_service import get_summary


def life_balance_insights(days: int = 7) -> list[dict]:
    """
    Detect simple imbalance patterns from bucket distribution.
    Returns insight dicts compatible with proactive engine format.
    """
    summary = get_summary(days=days)
    if summary["event_count"] < 3:
        return []

    insights: list[dict] = []
    for item in summary.get("by_top_level", []):
        category = item["category"]
        percent = item["percent"]
        if category == "Work" and percent >= 70:
            insights.append({
                "type": "balance",
                "title": "Heavy work week",
                "body": f"{percent}% of captured activity was Work over the last {days} days.",
                "action_label": "View buckets",
                "action_url": "/buckets",
                "urgency": 1,
            })
        if category == "Health" and percent <= 5 and summary["event_count"] >= 10:
            insights.append({
                "type": "balance",
                "title": "Low health signal",
                "body": f"Only {percent}% of activity was Health-related this week.",
                "action_label": "View buckets",
                "action_url": "/buckets",
                "urgency": 1,
            })
        if category == "People" and percent <= 5 and summary["event_count"] >= 10:
            insights.append({
                "type": "balance",
                "title": "Light on relationships",
                "body": f"People were {percent}% of activity — consider reaching out.",
                "action_label": "View people",
                "action_url": "/relationships",
                "urgency": 1,
            })

    return insights[:3]
