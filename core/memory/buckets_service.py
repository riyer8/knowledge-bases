"""Life bucket taxonomy, summaries, and tree views."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from core.config import config
from core.memory.bucket_classifier import _BUCKETS, _load_classifications, override_bucket


def get_taxonomy() -> dict[str, Any]:
    """Return the bucket tree and flat leaf list."""
    tree: dict[str, list[str]] = defaultdict(list)
    for leaf in _BUCKETS:
        if "/" in leaf:
            parent, child = leaf.split("/", 1)
            tree[parent].append(child)
        else:
            tree[leaf] = []

    return {
        "leaves": list(_BUCKETS),
        "tree": {parent: sorted(children) for parent, children in sorted(tree.items())},
    }


def _parse_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iter_clean_events(since: datetime | None = None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    clean_dir = config.events_clean_dir
    if not clean_dir.exists():
        return events

    for log_file in sorted(clean_dir.glob("*.jsonl")):
        for line in log_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since:
                ts = _parse_ts(str(event.get("timestamp", "")))
                if ts is None or ts < since:
                    continue
            events.append(event)
    return events


def get_summary(days: int = 7) -> dict[str, Any]:
    """Count classified events per bucket over the last N days."""
    days = max(1, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    classifications = _load_classifications()
    events_by_id = {e["id"]: e for e in _iter_clean_events(since) if e.get("id")}

    counts: dict[str, int] = defaultdict(int)
    matched = 0
    for event_id, meta in classifications.items():
        if event_id not in events_by_id:
            continue
        bucket = str(meta.get("bucket", "Other"))
        counts[bucket] += 1
        matched += 1

    total = sum(counts.values()) or 1
    breakdown = [
        {
            "bucket": bucket,
            "count": count,
            "percent": round(100.0 * count / total, 1),
        }
        for bucket, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]

    top_level: dict[str, int] = defaultdict(int)
    for item in breakdown:
        parent = item["bucket"].split("/", 1)[0]
        top_level[parent] += item["count"]

    return {
        "days": days,
        "event_count": matched,
        "breakdown": breakdown,
        "by_top_level": [
            {"category": k, "count": v, "percent": round(100.0 * v / total, 1)}
            for k, v in sorted(top_level.items(), key=lambda x: -x[1])
        ],
    }


def list_events_for_bucket(bucket: str, days: int = 7, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent events classified into a bucket."""
    days = max(1, min(days, 90))
    limit = max(1, min(limit, 200))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    classifications = _load_classifications()
    events_by_id = {e["id"]: e for e in _iter_clean_events(since) if e.get("id")}

    results: list[dict[str, Any]] = []
    for event_id, meta in classifications.items():
        if str(meta.get("bucket")) != bucket:
            continue
        event = events_by_id.get(event_id)
        if not event:
            continue
        text = str(event.get("content", {}).get("text", ""))[:300]
        results.append({
            "event_id": event_id,
            "timestamp": event.get("timestamp"),
            "source": event.get("source"),
            "bucket": bucket,
            "text_preview": text,
            "user_overridden": bool(meta.get("user_overridden")),
        })
        if len(results) >= limit:
            break

    results.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
    return results


def get_tree_view(days: int = 7) -> dict[str, Any]:
    """Grouped bucket view for UI tree filters."""
    summary = get_summary(days=days)
    tree: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in summary["breakdown"]:
        parent = item["bucket"].split("/", 1)[0]
        tree[parent].append(item)

    return {
        "days": days,
        "categories": [
            {"name": parent, "buckets": buckets, "total": sum(b["count"] for b in buckets)}
            for parent, buckets in sorted(tree.items())
        ],
    }


def list_recent_classified_events(days: int = 7, limit: int = 30) -> list[dict[str, Any]]:
    """Return recent classified events across all buckets for review UIs."""
    days = max(1, min(days, 90))
    limit = max(1, min(limit, 100))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    classifications = _load_classifications()
    events_by_id = {e["id"]: e for e in _iter_clean_events(since) if e.get("id")}

    results: list[dict[str, Any]] = []
    for event_id, meta in classifications.items():
        event = events_by_id.get(event_id)
        if not event:
            continue
        bucket = str(meta.get("bucket", "Other"))
        text = str(event.get("content", {}).get("text", ""))[:300]
        results.append({
            "event_id": event_id,
            "timestamp": event.get("timestamp"),
            "source": event.get("source"),
            "bucket": bucket,
            "text_preview": text,
            "user_overridden": bool(meta.get("user_overridden")),
            "classification_source": meta.get("source", "unknown"),
        })

    results.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
    return results[:limit]


def override_event_bucket(event_id: str, bucket: str) -> dict[str, str]:
    if bucket not in _BUCKETS:
        raise ValueError(f"unknown bucket: {bucket}")
    override_bucket(event_id, bucket)
    return {"event_id": event_id, "bucket": bucket}
