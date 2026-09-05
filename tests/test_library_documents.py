"""Tests for library title updates and document extraction."""
from __future__ import annotations

import json

import pytest


@pytest.fixture(autouse=True)
def library_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.library_service as lib
    reload(lib)
    yield lib


def test_update_page_title(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    page = library_env.save_page({
        "url": "https://example.com/doc",
        "title": "Original",
        "visible_text": "Some content",
    })
    updated = library_env.update_page_title(page["id"], "My Custom Title")
    assert updated["title"] == "My Custom Title"

    listed = library_env.list_saved_pages()
    assert listed[0]["title"] == "My Custom Title"


def test_update_page_metadata(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    page = library_env.save_page({
        "url": "https://example.com/meta",
        "title": "Paper",
        "visible_text": "Body",
    })
    updated = library_env.update_page(
        page["id"],
        metadata={
            "author": "Ada Lovelace",
            "date": "1843",
            "category": "science",
            "medium": "research paper",
            "notes": ":::quote\nA line from the paper\n:::\n\nWorth rereading.",
            "custom": [{"key": "Journal", "value": "Notes"}],
        },
    )
    assert updated["metadata"]["author"] == "Ada Lovelace"
    assert updated["metadata"]["category"] == "science"
    assert updated["metadata"]["medium"] == "research paper"
    assert ":::quote" in updated["metadata"]["notes"]
    assert updated["metadata"]["custom"][0]["key"] == "Journal"
    assert updated["metadata"]["dateAdded"]


def test_date_added_set_once(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    page = library_env.save_page({
        "url": "https://example.com/dated",
        "title": "Dated",
        "visible_text": "Body",
        "metadata": {"dateAdded": "2026-01-02", "notes": "> Hello"},
    })
    assert page["metadata"]["dateAdded"] == "2026-01-02"
    updated = library_env.update_page(page["id"], metadata={"notes": "> Hello\n\nMore"})
    assert updated["metadata"]["dateAdded"] == "2026-01-02"
    loaded = library_env.get_saved_page(page["id"])
    assert loaded["metadata"]["dateAdded"] == "2026-01-02"


def test_update_and_delete_quote(library_env, monkeypatch):
    monkeypatch.setattr(library_env, "ingest_text", lambda **kwargs: {"id": "e1"})

    quote = library_env.save_quote(
        text="First quote",
        page_url="https://example.com/q",
        page_title="Page",
    )
    updated = library_env.update_quote(quote["id"], text="Edited quote", note="note")
    assert updated["text"] == "Edited quote"
    assert updated["note"] == "note"

    assert library_env.delete_quote(quote["id"]) is True
    assert library_env.delete_quote(quote["id"]) is False
    assert library_env.list_quotes(page_url="https://example.com/q") == []


def test_extract_document_context_uses_pdf_extractor(library_env, monkeypatch):
    monkeypatch.setattr(
        library_env,
        "_extract_pdf_text",
        lambda data, max_pages=40: "Hello from PDF document body",
    )
    import base64

    page = library_env.extract_document_context(
        url="https://example.com/sample.pdf",
        content_base64=base64.b64encode(b"%PDF-fake").decode("ascii"),
        title="My PDF",
    )
    assert page["page_type"] == "pdf"
    assert page["title"] == "My PDF"
    assert "Hello from PDF" in page["visible_text"]
