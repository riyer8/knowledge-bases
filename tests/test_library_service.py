"""Tests for the saved-page library service."""
from __future__ import annotations

import json
from importlib import reload

import pytest


@pytest.fixture
def library_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.library_service as lib
    reload(lib)
    return lib


def test_save_and_list_pages(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Test summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    page = library_env.save_page({
        "url": "https://example.com/a",
        "title": "Article A",
        "visible_text": "Some content about transformers.",
    })
    assert page["id"]
    assert page["summary"] == "Test summary"

    pages = library_env.list_saved_pages()
    assert len(pages) == 1
    assert pages[0]["title"] == "Article A"


def test_save_quote(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(library_env, "remember_concept", lambda **kwargs: {"id": "c1"})

    saved = library_env.save_page({
        "url": "https://example.com/b",
        "title": "Article B",
        "visible_text": "Content",
    })
    quote = library_env.save_quote(
        text="An important passage",
        page_id=saved["id"],
        page_url=saved["url"],
        page_title=saved["title"],
        note="key idea",
    )
    assert quote["id"]
    quotes = library_env.list_quotes(page_id=saved["id"])
    assert len(quotes) == 1
    assert quotes[0]["text"] == "An important passage"


def test_chat_history_persisted(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    saved = library_env.save_page({
        "url": "https://example.com/c",
        "title": "Article C",
        "visible_text": "Content",
    }, chat_history=[{"role": "user", "content": "Hello"}])

    page = library_env.get_saved_page(saved["id"])
    assert page is not None
    assert page["chat_history"][0]["content"] == "Hello"

    library_env.append_chat_turn(saved["id"], "assistant", "Hi there")
    history = library_env.load_chat_history(saved["id"])
    assert len(history) == 2


def test_delete_saved_page(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(library_env, "remember_concept", lambda **kwargs: {"id": "c1"})

    saved = library_env.save_page({
        "url": "https://example.com/d",
        "title": "Article D",
        "visible_text": "Content",
    })
    library_env.save_quote(text="quote", page_id=saved["id"])
    assert library_env.delete_saved_page(saved["id"])
    assert library_env.get_saved_page(saved["id"]) is None
    assert library_env.list_saved_pages() == []


def test_explore_suggestions(library_env, monkeypatch):
    monkeypatch.setattr(
        library_env,
        "provider_chat",
        lambda messages, stream=False, max_tokens=None: "Topic A\nTopic B\nTopic C",
    )
    suggestions = library_env.explore_suggestions({
        "title": "Test",
        "visible_text": "Some page content",
    })
    assert suggestions == ["Topic A", "Topic B", "Topic C"]


def test_graph_visual(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(library_env, "related_for_page", lambda **kwargs: [])
    monkeypatch.setattr(library_env, "list_concepts", lambda limit=50: [])

    library_env.save_page({
        "url": "https://example.com/e",
        "title": "Graph Page",
        "visible_text": "Content",
    })
    library_env.save_quote(
        text="A quote that should not appear as its own node",
        page_url="https://example.com/e",
        page_title="Graph Page",
    )
    graph = library_env.graph_visual()
    assert any(n["type"] == "page" for n in graph["nodes"])
    assert not any(n["type"] == "quote" for n in graph["nodes"])
    assert len(graph["nodes"]) == 1


def test_list_quotes_by_page_url(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(library_env, "remember_concept", lambda **kwargs: {"id": "c1"})

    library_env.save_quote(
        text="Before page saved",
        page_url="https://example.com/x",
        page_title="X",
    )
    quotes = library_env.list_quotes(page_url="https://example.com/x")
    assert len(quotes) == 1
    assert quotes[0]["text"] == "Before page saved"


def test_list_quotes_by_url(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    library_env.save_quote(
        text="url quote",
        page_url="https://example.com/x",
        page_title="X",
    )
    quotes = library_env.list_quotes(page_url="https://example.com/x")
    assert len(quotes) == 1


def test_clear_library(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    library_env.save_page({
        "url": "https://example.com/f",
        "title": "To clear",
        "visible_text": "Content",
    })
    library_env.clear_library()
    assert library_env.list_saved_pages() == []
