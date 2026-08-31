"""Tests for concept knowledge graph."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.memory.concept_graph as cg
    reload(cg)
    yield tmp_path


def test_remember_concept_creates_node(monkeypatch):
    monkeypatch.setattr(
        "core.memory.concept_graph._extract_concept_metadata",
        lambda passage, page_title="", note="": {
            "name": "Scaling Laws",
            "related": ["Transformers"],
        },
    )
    from core.memory.concept_graph import get_concept, remember_concept

    concept = remember_concept(
        passage="Scaling laws predict model performance",
        page_id="page-1",
        page_title="Scaling Laws Paper",
        page_url="https://example.com/paper",
        note="important",
        event_id="event-1",
    )
    assert concept["name"] == "Scaling Laws"
    assert concept["times_referenced"] == 1
    loaded = get_concept(concept["id"])
    assert loaded is not None
    assert loaded["notes"] == ["important"]


def test_remember_concept_strengthens_existing(monkeypatch):
    monkeypatch.setattr(
        "core.memory.concept_graph._extract_concept_metadata",
        lambda passage, page_title="", note="": {"name": "Attention", "related": []},
    )
    from core.memory.concept_graph import remember_concept

    first = remember_concept(
        passage="Attention is all you need",
        page_id="p1",
        page_title="Paper A",
        page_url="https://a.test",
    )
    second = remember_concept(
        passage="Attention mechanisms again",
        page_id="p2",
        page_title="Paper B",
        page_url="https://b.test",
    )
    assert first["id"] == second["id"]
    assert second["times_referenced"] == 2
    assert second["understanding_score"] > first["understanding_score"]


def test_related_for_page_matches_url(monkeypatch):
    monkeypatch.setattr(
        "core.memory.concept_graph._extract_concept_metadata",
        lambda passage, page_title="", note="": {"name": "Graph Theory", "related": []},
    )
    from core.memory.concept_graph import related_for_page, remember_concept

    remember_concept(
        passage="Nodes and edges",
        page_id="p1",
        page_title="Graph intro",
        page_url="https://example.com/graph",
    )
    related = related_for_page(page_url="https://example.com/graph")
    assert len(related) == 1
    assert related[0]["name"] == "Graph Theory"


def test_list_concepts_search(monkeypatch):
    monkeypatch.setattr(
        "core.memory.concept_graph._extract_concept_metadata",
        lambda passage, page_title="", note="": {"name": passage[:20], "related": []},
    )
    from core.memory.concept_graph import list_concepts, remember_concept

    remember_concept(passage="Transformers overview", page_id="1", page_title="T", page_url="https://t")
    remember_concept(passage="Cooking pasta", page_id="2", page_title="C", page_url="https://c")
    results = list_concepts(query="transform")
    assert len(results) == 1
