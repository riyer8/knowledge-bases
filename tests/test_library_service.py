"""Tests for the saved-page library service."""
from __future__ import annotations

import json
import threading
from importlib import reload

import pytest


@pytest.fixture
def library_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.memory.bucket_classifier as bc_mod
    import core.memory.buckets_service as bs_mod
    reload(bc_mod)
    reload(bs_mod)
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


def test_save_page_returns_before_llm(library_env, monkeypatch):
    release = threading.Event()

    def slow_summary(page):
        release.wait(timeout=2)
        return "LLM summary"

    monkeypatch.setattr(library_env, "_generate_summary", slow_summary)
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    page = library_env.save_page({
        "url": "https://example.com/fast",
        "title": "Fast Save",
        "headings": ["Alpha", "Beta"],
        "visible_text": "Hello",
    }, background=True)

    assert page["summary"] == "- Alpha\n- Beta"
    listed = library_env.list_saved_pages()
    assert listed[0]["id"] == page["id"]
    release.set()
    for _ in range(50):
        loaded = library_env.get_saved_page(page["id"])
        if loaded and loaded.get("summary") == "LLM summary":
            break
        threading.Event().wait(0.02)
    else:
        raise AssertionError("background summary never landed")


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


def test_save_quote_dedupes_same_passage(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(library_env, "remember_concept", lambda **kwargs: {"id": "c1"})

    saved = library_env.save_page({
        "url": "https://example.com/dedupe",
        "title": "Dedupe",
        "visible_text": "Content",
    })
    first = library_env.save_quote(
        text="Same passage",
        page_id=saved["id"],
        page_url=saved["url"],
        page_title=saved["title"],
    )
    second = library_env.save_quote(
        text="Same passage",
        page_id=saved["id"],
        page_url=saved["url"],
        page_title=saved["title"],
        note="added later",
    )
    assert second["id"] == first["id"]
    assert second["note"] == "added later"
    assert len(library_env.list_quotes(page_id=saved["id"])) == 1


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
        lambda messages, stream=False, max_tokens=None: json.dumps([
            {"title": "Topic A", "url": "https://example.com/a"},
            {"title": "Topic B", "url": "https://example.com/b"},
            {"title": "Topic C", "url": "https://example.com/c"},
        ]),
    )
    suggestions = library_env.explore_suggestions({
        "title": "Test",
        "visible_text": "Some page content",
        "links": [{"text": "On page", "href": "https://example.com/page-link"}],
    })
    assert len(suggestions) == 10
    assert suggestions[0]["title"] == "Topic A"
    assert suggestions[0]["url"] == "https://example.com/a"
    assert any(item["url"] == "https://example.com/page-link" for item in suggestions)


def test_graph_visual(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(library_env, "related_for_page", lambda **kwargs: [])

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


def test_save_page_links_orphan_quotes_by_url(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(library_env, "remember_concept", lambda **kwargs: {"id": "c1"})

    quote = library_env.save_quote(
        text="Saved before page",
        page_url="https://example.com/link",
        page_title="Link",
    )
    assert not quote["page_id"]

    saved = library_env.save_page({
        "url": "https://example.com/link",
        "title": "Link",
        "visible_text": "Content",
    })
    quotes = library_env.list_quotes(page_id=saved["id"])
    assert len(quotes) == 1
    assert quotes[0]["id"] == quote["id"]


def test_list_quotes_by_url(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    library_env.save_quote(
        text="url quote",
        page_url="https://example.com/x",
        page_title="X",
    )
    quotes = library_env.list_quotes(page_url="https://example.com/x")
    assert len(quotes) == 1


def test_list_quotes_matches_canonical_url(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})
    library_env.save_quote(
        text="hashed quote text",
        page_url="https://example.com/article/#section",
        page_title="Article",
    )
    quotes = library_env.list_quotes(page_url="https://example.com/article")
    assert len(quotes) == 1
    assert quotes[0]["text"] == "hashed quote text"


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


def test_normalize_title_collapses_whitespace(library_env):
    assert library_env._normalize_title("Hello\n\n  world\t title") == "Hello world title"
    assert library_env._normalize_title("   ") == "Untitled page"
    assert library_env._normalize_title("", empty="") == ""


def test_save_and_update_page_normalize_title(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    page = library_env.save_page({
        "url": "https://example.com/title-gaps",
        "title": "Hello\n\nworld",
        "visible_text": "Content",
    })
    assert page["title"] == "Hello world"
    listed = library_env.list_saved_pages()
    assert listed[0]["title"] == "Hello world"

    updated = library_env.update_page(page["id"], title="Fresh\n\n  title")
    assert updated["title"] == "Fresh title"
    loaded = library_env.get_saved_page(page["id"])
    assert loaded["title"] == "Fresh title"


def test_get_saved_page_heals_legacy_multiline_title(library_env, monkeypatch, tmp_path):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    page = library_env.save_page({
        "url": "https://example.com/legacy-title",
        "title": "Normal",
        "visible_text": "Content",
    })
    path = library_env._page_path(page["id"])
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["title"] = "Broken\n\nTitle"
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    index = library_env._load_saved_index()
    for entry in index:
        if entry.get("id") == page["id"]:
            entry["title"] = "Broken\n\nTitle"
    library_env._save_saved_index(index)

    healed = library_env.get_saved_page(page["id"])
    assert healed["title"] == "Broken Title"
    assert json.loads(path.read_text(encoding="utf-8"))["title"] == "Broken Title"
