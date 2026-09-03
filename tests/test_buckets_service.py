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


def _write_event(
    kb_root,
    event_id: str,
    text: str,
    source: str = "manual_text",
    metadata: dict | None = None,
) -> None:
    clean_dir = kb_root / "events" / "clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    log = clean_dir / "2026-05-27.jsonl"
    event = {
        "id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "content": {"text": text, "metadata": metadata or {}},
    }
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def _write_saved_page(kb_root, page_id: str, title: str = "Saved article") -> None:
    lib = kb_root / "library"
    (lib / "pages").mkdir(parents=True, exist_ok=True)
    index = [{"id": page_id, "title": title, "url": "https://example.com/a"}]
    (lib / "saved_pages.json").write_text(json.dumps(index), encoding="utf-8")
    (lib / "pages" / f"{page_id}.json").write_text(
        json.dumps({"id": page_id, "title": title, "url": "https://example.com/a"}),
        encoding="utf-8",
    )


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
    assert "Work/Projects" in tax["leaves"]
    assert "News" in tax["leaves"]
    assert "Work" in tax["tree"]
    assert "Projects" in tax["tree"]["Work"]
    assert tax["tree"]["News"] == []


def test_get_summary_counts_buckets(isolated_kb):
    _write_event(isolated_kb, "e1", "standup with the team")
    _write_event(isolated_kb, "e2", "gym workout")
    _write_classification(isolated_kb, "e1", "Work/Meetings")
    _write_classification(isolated_kb, "e2", "Health/Fitness")

    from core.memory.buckets_service import get_summary

    summary = get_summary(days=7)
    assert summary["event_count"] == 2
    buckets = {item["bucket"]: item["count"] for item in summary["breakdown"]}
    assert buckets["Work/Meetings"] == 1
    assert buckets["Health/Fitness"] == 1


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
    override_event_bucket("e1", "Entertainment")

    events = list_events_for_bucket("Entertainment", days=7)
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
    _write_classification(isolated_kb, "e2", "Health/Fitness")

    from core.memory.buckets_service import list_recent_classified_events

    events = list_recent_classified_events(days=7, limit=10)
    assert len(events) == 2
    buckets = {e["event_id"]: e["bucket"] for e in events}
    assert buckets["e1"] == "Work/Meetings"
    assert buckets["e2"] == "Health/Fitness"


def test_unsaved_article_events_hidden_from_life(isolated_kb):
    _write_event(
        isolated_kb,
        "q1",
        "Quote from an unsaved article",
        source="saved_quote",
        metadata={"page_id": "", "quote_id": "quote-unsaved", "title": "Draft"},
    )
    _write_classification(isolated_kb, "q1", "Learning/Research")

    from core.memory.buckets_service import get_summary, list_recent_classified_events

    assert list_recent_classified_events(days=7) == []
    assert get_summary(days=7)["event_count"] == 0


def test_saved_article_events_visible_in_life(isolated_kb):
    _write_saved_page(isolated_kb, "page-1", "Saved article")
    _write_event(
        isolated_kb,
        "p1",
        "Saved page: Saved article",
        source="saved_page",
        metadata={"page_id": "page-1", "title": "Saved article", "url": "https://example.com/a"},
    )
    _write_classification(isolated_kb, "p1", "News")

    from core.memory.buckets_service import list_recent_classified_events

    events = list_recent_classified_events(days=7)
    assert len(events) == 1
    assert events[0]["title"] == "Saved article"
    assert events[0]["bucket"] == "News"


def test_non_library_events_still_visible(isolated_kb):
    _write_event(isolated_kb, "g1", "Q3 planning review", source="gcal")
    _write_classification(isolated_kb, "g1", "Work/Admin")

    from core.memory.buckets_service import list_recent_classified_events

    events = list_recent_classified_events(days=7)
    assert len(events) == 1
    assert events[0]["source"] == "gcal"


def test_legacy_bucket_names_are_mapped(isolated_kb):
    _write_event(isolated_kb, "e1", "legacy deep work")
    _write_classification(isolated_kb, "e1", "Work/Deep Work")

    from core.memory.buckets_service import list_recent_classified_events

    events = list_recent_classified_events(days=7)
    assert events[0]["bucket"] == "Work/Projects"


def test_forget_library_page_removes_life_event(isolated_kb):
    _write_saved_page(isolated_kb, "page-2")
    _write_event(
        isolated_kb,
        "p2",
        "Saved page",
        source="saved_page",
        metadata={"page_id": "page-2", "title": "Gone"},
    )
    _write_classification(isolated_kb, "p2", "News")

    from core.memory.buckets_service import forget_library_page, list_recent_classified_events

    forget_library_page("page-2")
    assert list_recent_classified_events(days=7) == []


def test_quote_appears_once_page_is_saved(isolated_kb):
    _write_saved_page(isolated_kb, "page-3")
    quotes_dir = isolated_kb / "library"
    quotes_dir.mkdir(parents=True, exist_ok=True)
    (quotes_dir / "quotes.json").write_text(
        json.dumps([{"id": "quote-1", "page_id": "page-3", "text": "A line"}]),
        encoding="utf-8",
    )
    _write_event(
        isolated_kb,
        "q2",
        "Quote from later-saved article",
        source="saved_quote",
        metadata={"page_id": "", "quote_id": "quote-1", "title": "Later saved"},
    )
    _write_classification(isolated_kb, "q2", "Learning/Research")

    from core.memory.buckets_service import list_recent_classified_events

    events = list_recent_classified_events(days=7)
    assert len(events) == 1
    assert events[0]["event_id"] == "q2"
