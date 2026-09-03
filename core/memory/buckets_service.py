"""Life bucket taxonomy, summaries, and tree views."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from core.config import config
from core.memory.bucket_classifier import (
    _BUCKETS,
    _LEGACY_BUCKETS,
    _TOP_LEVEL_ORDER,
    _load_classifications,
    normalize_bucket,
    override_bucket,
    remove_classifications,
)

_LIBRARY_SOURCES = frozenset({"saved_page", "saved_quote", "browser_remember"})


def get_taxonomy() -> dict[str, Any]:
    """Return the bucket tree and flat leaf list."""
    tree: dict[str, list[str]] = {}
    for leaf in _BUCKETS:
        if "/" in leaf:
            parent, child = leaf.split("/", 1)
            tree.setdefault(parent, []).append(child)
        else:
            tree.setdefault(leaf, [])

    ordered: dict[str, list[str]] = {}
    for parent in _TOP_LEVEL_ORDER:
        if parent in tree:
            ordered[parent] = tree[parent]
    for parent, children in tree.items():
        if parent not in ordered:
            ordered[parent] = children

    return {
        "leaves": list(_BUCKETS),
        "tree": ordered,
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


def _event_metadata(event: dict[str, Any]) -> dict[str, Any]:
    meta = (event.get("content") or {}).get("metadata") or {}
    return meta if isinstance(meta, dict) else {}


def _saved_page_ids() -> set[str]:
    path = config.kb_root / "library" / "saved_pages.json"
    if not path.exists():
        return set()
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(entries, list):
        return set()
    return {str(entry["id"]) for entry in entries if isinstance(entry, dict) and entry.get("id")}


def _quote_page_id(quote_id: str) -> str:
    if not quote_id:
        return ""
    path = config.kb_root / "library" / "quotes.json"
    if not path.exists():
        return ""
    try:
        quotes = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(quotes, list):
        return ""
    for quote in quotes:
        if isinstance(quote, dict) and str(quote.get("id") or "") == quote_id:
            return str(quote.get("page_id") or "").strip()
    return ""


def _library_page_id_for_event(event: dict[str, Any]) -> str:
    meta = _event_metadata(event)
    page_id = str(meta.get("page_id") or "").strip()
    if page_id:
        return page_id
    return _quote_page_id(str(meta.get("quote_id") or "").strip())


def event_belongs_in_life(event: dict[str, Any], saved_ids: set[str] | None = None) -> bool:
    """Reading events only belong in Life if the page is still saved."""
    source = str(event.get("source") or "")
    if source not in _LIBRARY_SOURCES:
        return True
    saved_ids = _saved_page_ids() if saved_ids is None else saved_ids
    page_id = _library_page_id_for_event(event)
    return bool(page_id) and page_id in saved_ids


def _visible_events_by_id(since: datetime | None = None) -> dict[str, dict[str, Any]]:
    saved_ids = _saved_page_ids()
    visible: dict[str, dict[str, Any]] = {}
    for event in _iter_clean_events(since):
        event_id = event.get("id")
        if not event_id:
            continue
        if event_belongs_in_life(event, saved_ids):
            visible[str(event_id)] = event
    return visible


def _event_payload(event_id: str, event: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    content_meta = _event_metadata(event)
    text = str(event.get("content", {}).get("text", ""))[:300]
    bucket = normalize_bucket(str(meta.get("bucket", "Other")))
    return {
        "event_id": event_id,
        "timestamp": event.get("timestamp"),
        "source": event.get("source"),
        "bucket": bucket,
        "text_preview": text,
        "title": str(content_meta.get("title") or ""),
        "url": str(content_meta.get("url") or ""),
        "page_id": str(content_meta.get("page_id") or ""),
        "user_overridden": bool(meta.get("user_overridden")),
        "classification_source": meta.get("source", "unknown"),
    }


def get_summary(days: int = 7) -> dict[str, Any]:
    """Count classified events per bucket over the last N days."""
    days = max(1, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    classifications = _load_classifications()
    events_by_id = _visible_events_by_id(since)

    counts: dict[str, int] = defaultdict(int)
    matched = 0
    for event_id, meta in classifications.items():
        if event_id not in events_by_id:
            continue
        bucket = normalize_bucket(str(meta.get("bucket", "Other")))
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
            for k, v in sorted(
                top_level.items(),
                key=lambda x: (
                    _TOP_LEVEL_ORDER.index(x[0]) if x[0] in _TOP_LEVEL_ORDER else 99,
                    -x[1],
                ),
            )
        ],
    }


def list_events_for_bucket(bucket: str, days: int = 7, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent events classified into a bucket."""
    bucket = normalize_bucket(bucket)
    days = max(1, min(days, 90))
    limit = max(1, min(limit, 200))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    classifications = _load_classifications()
    events_by_id = _visible_events_by_id(since)

    results: list[dict[str, Any]] = []
    for event_id, meta in classifications.items():
        if normalize_bucket(str(meta.get("bucket"))) != bucket:
            continue
        event = events_by_id.get(event_id)
        if not event:
            continue
        results.append(_event_payload(event_id, event, meta))
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

    categories = []
    seen: set[str] = set()
    for parent in _TOP_LEVEL_ORDER:
        if parent not in tree:
            continue
        buckets = tree[parent]
        categories.append({
            "name": parent,
            "buckets": buckets,
            "total": sum(b["count"] for b in buckets),
        })
        seen.add(parent)
    for parent, buckets in tree.items():
        if parent in seen:
            continue
        categories.append({
            "name": parent,
            "buckets": buckets,
            "total": sum(b["count"] for b in buckets),
        })

    return {
        "days": days,
        "categories": categories,
    }


def list_recent_classified_events(days: int = 7, limit: int = 30) -> list[dict[str, Any]]:
    """Return recent classified events across all buckets for review UIs."""
    days = max(1, min(days, 90))
    limit = max(1, min(limit, 100))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    classifications = _load_classifications()
    events_by_id = _visible_events_by_id(since)

    results: list[dict[str, Any]] = []
    for event_id, meta in classifications.items():
        event = events_by_id.get(event_id)
        if not event:
            continue
        results.append(_event_payload(event_id, event, meta))

    results.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
    return results[:limit]


def override_event_bucket(event_id: str, bucket: str) -> dict[str, str]:
    mapped = _LEGACY_BUCKETS.get(bucket, bucket)
    if mapped not in _BUCKETS:
        raise ValueError(f"unknown bucket: {bucket}")
    override_bucket(event_id, mapped)
    return {"event_id": event_id, "bucket": mapped}


def forget_library_page(page_id: str) -> None:
    """Drop Life classifications for a saved page that was removed."""
    page_id = (page_id or "").strip()
    if not page_id:
        return
    drop: set[str] = set()
    for event in _iter_clean_events():
        event_id = str(event.get("id") or "")
        if not event_id:
            continue
        if _library_page_id_for_event(event) == page_id:
            drop.add(event_id)
    remove_classifications(drop)


def forget_library_quote(quote_id: str) -> None:
    quote_id = (quote_id or "").strip()
    if not quote_id:
        return
    drop: set[str] = set()
    for event in _iter_clean_events():
        event_id = str(event.get("id") or "")
        meta = _event_metadata(event)
        if event_id and str(meta.get("quote_id") or "") == quote_id:
            drop.add(event_id)
    remove_classifications(drop)


def forget_all_library_events() -> None:
    """Drop Life classifications for every library-backed reading event."""
    drop: set[str] = set()
    for event in _iter_clean_events():
        event_id = str(event.get("id") or "")
        if event_id and str(event.get("source") or "") in _LIBRARY_SOURCES:
            drop.add(event_id)
    remove_classifications(drop)
