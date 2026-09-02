"""Tests for the LLM-maintained wiki service."""
from __future__ import annotations

import json
from importlib import reload

import pytest


@pytest.fixture
def wiki_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.wiki_service as wiki
    reload(wiki)
    return wiki


def test_ingest_and_list_raw(wiki_env):
    record = wiki_env.ingest_raw(
        "Scaling Laws",
        "Model performance scales with compute and data.",
        url="https://example.com/scaling",
        source_type="page",
    )
    assert record["id"]
    raw_list = wiki_env.list_raw()
    assert len(raw_list) == 1
    assert raw_list[0]["title"] == "Scaling Laws"
    assert raw_list[0]["compiled"] is False

    raw = wiki_env.get_raw(record["id"])
    assert raw is not None
    assert "Scaling Laws" in raw["content"]


def test_search_wiki(wiki_env):
    wiki_env.ingest_raw("Transformers", "Attention is all you need.")
    hits = wiki_env.search_wiki("attention")
    assert len(hits) == 1
    assert hits[0]["title"] == "Transformers"


def test_compile_wiki_updates_articles(wiki_env, monkeypatch):
    wiki_env.ingest_raw("Neural Scaling", "Performance improves with scale.")

    def fake_chat(messages, **kwargs):
        return json.dumps({
            "articles": [{
                "slug": "neural-scaling",
                "title": "Neural Scaling",
                "content": "Key idea: bigger models work better.\n\nSee also [[transformers]].",
                "update_index_line": "- [[neural-scaling]] — scaling behavior",
            }],
        })

    monkeypatch.setattr(wiki_env, "provider_chat", fake_chat)
    result = wiki_env.compile_wiki(max_sources=1)
    assert result["compiled"] == 1
    assert "neural-scaling" in result["articles_updated"]

    articles = wiki_env.list_articles()
    assert len(articles) == 1
    article = wiki_env.get_article("neural-scaling")
    assert article is not None
    assert "bigger models" in article["content"]
    assert wiki_env.read_index().find("neural-scaling") >= 0

    raw_list = wiki_env.list_raw()
    assert raw_list[0]["compiled"] is True


def test_health_check(wiki_env, monkeypatch):
    wiki_env.ingest_raw("Topic", "Some content.")

    monkeypatch.setattr(
        wiki_env,
        "provider_chat",
        lambda messages, **kwargs: json.dumps({
            "issues": [{"severity": "low", "message": "Index is sparse"}],
            "suggestions": ["What relates to Topic?"],
            "new_article_ideas": ["Topic overview"],
        }),
    )
    result = wiki_env.health_check()
    assert result["ok"] is True
    assert result["issues"][0]["message"] == "Index is sparse"


def test_wiki_status(wiki_env):
    wiki_env.ingest_raw("A", "content a")
    status = wiki_env.wiki_status()
    assert status["raw_count"] == 1
    assert status["article_count"] == 0
    assert status["uncompiled_count"] == 1


def test_ask_wiki_uses_context(wiki_env, monkeypatch):
    wiki_env.ingest_raw("Scaling Laws", "Performance improves with compute and data size.")
    article_path = wiki_env._articles_dir() / "scaling-laws.md"
    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(
        '---\ntitle: "Scaling Laws"\n---\n\nBigger models tend to perform better.\n',
        encoding="utf-8",
    )

    captured: list[list[dict[str, str]]] = []

    def fake_chat(messages, **kwargs):
        captured.append(messages)
        return "Scaling laws say performance grows with compute."

    monkeypatch.setattr(wiki_env, "provider_chat", fake_chat)
    result = wiki_env.ask_wiki("What do scaling laws predict?")
    assert "Scaling laws" in result["reply"]
    assert "Scaling Laws" in result["sources"]
    assert any("Wiki context" in m.get("content", "") for m in captured[-1] if m["role"] == "user")


def test_ask_wiki_empty(wiki_env):
    result = wiki_env.ask_wiki("Anything?")
    assert "empty" in result["reply"].lower()
