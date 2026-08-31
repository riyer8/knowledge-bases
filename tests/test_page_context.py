"""Tests for page context service and extension backend support."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.page_context_service as pcs
    reload(pcs)
    yield tmp_path


def test_save_and_get_page_context():
    from core.page_context_service import get_page, save_page_context

    record = save_page_context({
        "url": "https://example.com/paper",
        "title": "Example Paper",
        "headings": ["Abstract"],
        "paragraphs": ["This is a test paragraph about transformers."],
        "visible_text": "Example visible text",
        "selected_text": "transformers",
        "page_type": "research_paper",
    })
    assert record["id"]
    assert record["title"] == "Example Paper"
    loaded = get_page(record["id"])
    assert loaded is not None
    assert loaded["url"] == "https://example.com/paper"


def test_history_lists_recent_pages():
    from core.page_context_service import list_history, save_page_context

    save_page_context({"url": "https://a.test", "title": "A"})
    save_page_context({"url": "https://b.test", "title": "B"})
    history = list_history(limit=10)
    assert len(history) == 2
    assert history[0]["title"] == "B"


def test_render_page_context_includes_title_and_selection():
    from core.page_context_service import render_page_context

    text = render_page_context({
        "title": "My Page",
        "url": "https://example.com",
        "selected_text": "important bit",
        "visible_text": "body text",
    })
    assert "My Page" in text
    assert "important bit" in text


def test_remember_passage_ingests_text(monkeypatch):
    from core.page_context_service import remember_passage, save_page_context

    page = save_page_context({"url": "https://example.com", "title": "Example"})
    captured: dict = {}

    def fake_ingest(text, source="manual_text", metadata=None, flagged_important=False):
        captured["text"] = text
        captured["source"] = source
        captured["metadata"] = metadata
        return {"id": "event-1"}

    monkeypatch.setattr("core.page_context_service.ingest_text", fake_ingest)
    monkeypatch.setattr(
        "core.page_context_service.remember_concept",
        lambda **kwargs: {
            "id": "concept:test",
            "name": "Scaling Laws",
            "understanding_score": 0.35,
            "related_names": ["Transformers"],
        },
    )
    result = remember_passage(page["id"], "Scaling laws matter", note="important")
    assert result["ok"] is True
    assert captured["source"] == "browser_remember"
    assert "Scaling laws matter" in captured["text"]


def test_get_connections_uses_memory_query(monkeypatch):
    from core.memory.vector_store import IndexedChunk
    from core.page_context_service import get_connections, save_page_context

    save_page_context({
        "url": "https://example.com/paper",
        "title": "Transformers",
        "visible_text": "attention is all you need",
    })

    chunk = IndexedChunk(
        event_id="e1",
        chunk_index=0,
        text="Earlier reading about transformers.",
        source="browser_remember",
        timestamp="2026-08-30T00:00:00Z",
        flagged_important=True,
        sensitivity_score=0.0,
        vector=[],
    )
    monkeypatch.setattr("core.page_context_service.memory_query", lambda q, top_k=5: [chunk])
    monkeypatch.setattr("core.page_context_service.related_for_page", lambda **kwargs: [])
    connections = get_connections(url="https://example.com/paper", top_k=3)
    assert len(connections) == 1
    assert connections[0]["type"] == "memory"
    assert "transformers" in connections[0]["text"].lower()
