"""Tests for core/memory/buckets_service.py."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.memory.bucket_classifier as bc_mod
    import core.memory.buckets_service as bs_mod
    reload(bc_mod)
    reload(bs_mod)
    cfg_mod.config.ensure_dirs()
    yield tmp_path


def _write_event(kb_root, event_id: str, text: str, source: str = "manual_text") -> None:
    clean_dir = kb_root / "events" / "clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    log = clean_dir / "2026-05-27.jsonl"
    event = {
        "id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "content": {"text": text},
    }
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def _write_classification(kb_root, event_id: str, bucket: str) -> None:
    buckets_dir = kb_root / "buckets"
    buckets_dir.mkdir(parents=True, exist_ok=True)
    path = buckets_dir / "classifications.json"
    data = {}
    if path.exists():
        data = json.loads(path.read_text())
    data[event_id] = {"bucket": bucket, "confidence": 1.0, "source": "test"}
    path.write_text(json.dumps(data))


def test_get_taxonomy_has_leaves_and_tree():
    from core.memory.buckets_service import get_taxonomy

    tax = get_taxonomy()
    assert "Work/Deep Work" in tax["leaves"]
    assert "Work" in tax["tree"]
    assert "Deep Work" in tax["tree"]["Work"]


def test_get_summary_counts_buckets(isolated_kb):
    _write_event(isolated_kb, "e1", "standup with the team")
    _write_event(isolated_kb, "e2", "gym workout")
    _write_classification(isolated_kb, "e1", "Work/Meetings")
    _write_classification(isolated_kb, "e2", "Health/Exercise")

    from core.memory.buckets_service import get_summary

    summary = get_summary(days=7)
    assert summary["event_count"] == 2
    buckets = {item["bucket"]: item["count"] for item in summary["breakdown"]}
    assert buckets["Work/Meetings"] == 1
    assert buckets["Health/Exercise"] == 1


def test_list_events_for_bucket(isolated_kb):
    _write_event(isolated_kb, "e1", "sprint planning meeting")
    _write_classification(isolated_kb, "e1", "Work/Meetings")

    from core.memory.buckets_service import list_events_for_bucket

    events = list_events_for_bucket("Work/Meetings", days=7)
    assert len(events) == 1
    assert events[0]["event_id"] == "e1"
    assert "meeting" in events[0]["text_preview"]


def test_override_event_bucket(isolated_kb):
    from core.memory.buckets_service import list_events_for_bucket, override_event_bucket

    _write_event(isolated_kb, "e1", "reading a book")
    override_event_bucket("e1", "Entertainment/Media")

    events = list_events_for_bucket("Entertainment/Media", days=7)
    assert len(events) == 1
    assert events[0]["user_overridden"] is True


def test_override_rejects_unknown_bucket():
    from core.memory.buckets_service import override_event_bucket

    with pytest.raises(ValueError, match="unknown bucket"):
        override_event_bucket("e1", "Not/A/Bucket")


def test_list_recent_classified_events(isolated_kb):
    _write_event(isolated_kb, "e1", "team standup meeting")
    _write_event(isolated_kb, "e2", "gym workout")
    _write_classification(isolated_kb, "e1", "Work/Meetings")
    _write_classification(isolated_kb, "e2", "Health/Exercise")

    from core.memory.buckets_service import list_recent_classified_events

    events = list_recent_classified_events(days=7, limit=10)
    assert len(events) == 2
    buckets = {e["event_id"]: e["bucket"] for e in events}
    assert buckets["e1"] == "Work/Meetings"
    assert buckets["e2"] == "Health/Exercise"
