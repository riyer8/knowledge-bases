"""
Tests for core/memory/. Run with: pytest tests/test_memory.py
Requires Ollama running locally with nomic-embed-text pulled.
Tests that don't need Ollama are marked; Ollama-dependent tests are skipped if unreachable.
"""
from __future__ import annotations

import json
import os
import uuid
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.memory.bucket_classifier as bc
    import core.memory.graph as g
    import core.memory.vector_store as vs
    import core.memory.store as st
    for mod in (bc, g, vs, st):
        reload(mod)
    yield tmp_path


def _make_event(text: str, source: str = "screen_capture") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "timestamp": "2026-05-27T10:00:00Z",
        "source": source,
        "content": {"text": text, "metadata": {}},
        "capture_context": {},
        "flagged_important": False,
        "sensitivity_score": 0.1,
        "entities": [],
        "raw_event": False,
    }


# --- Chunker ---

def test_short_text_produces_single_chunk():
    from core.memory.chunker import chunk_event
    event = _make_event("Short note.")
    chunks = chunk_event(event)
    assert len(chunks) == 1
    assert chunks[0].text == "Short note."
    assert chunks[0].chunk_index == 0


def test_long_text_produces_multiple_chunks():
    from core.memory.chunker import chunk_event
    long_text = "word " * 200  # ~1000 chars
    event = _make_event(long_text)
    chunks = chunk_event(event)
    assert len(chunks) > 1


def test_chunk_carries_event_metadata():
    from core.memory.chunker import chunk_event
    event = _make_event("Test note", source="gmail")
    event["flagged_important"] = True
    event["sensitivity_score"] = 0.7
    chunks = chunk_event(event)
    assert chunks[0].source == "gmail"
    assert chunks[0].flagged_important is True
    assert chunks[0].sensitivity_score == 0.7


def test_empty_text_produces_no_chunks():
    from core.memory.chunker import chunk_event
    event = _make_event("")
    assert chunk_event(event) == []


# --- Bucket classifier ---

def test_keyword_rule_classifies_meeting():
    from core.memory.bucket_classifier import classify_event
    event_id = str(uuid.uuid4())
    bucket = classify_event(event_id, "Had a zoom standup meeting with the team", "screen_capture")
    assert "Work" in bucket or "Meeting" in bucket


def test_keyword_rule_classifies_exercise():
    from core.memory.bucket_classifier import classify_event
    event_id = str(uuid.uuid4())
    bucket = classify_event(event_id, "Went for a morning run, 5km", "screen_capture")
    assert bucket == "Health/Exercise"


def test_gcal_source_classifies_as_work():
    from core.memory.bucket_classifier import classify_event
    event_id = str(uuid.uuid4())
    bucket = classify_event(event_id, "Q3 Planning Review", "gcal")
    assert bucket.startswith("Work")


def test_classification_is_persisted(tmp_path):
    from core.memory.bucket_classifier import classify_event
    event_id = str(uuid.uuid4())
    classify_event(event_id, "morning workout", "screen_capture")
    path = tmp_path / "buckets" / "classifications.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert event_id in data


def test_same_event_returns_same_bucket():
    from core.memory.bucket_classifier import classify_event
    event_id = str(uuid.uuid4())
    b1 = classify_event(event_id, "morning run", "screen_capture")
    b2 = classify_event(event_id, "morning run", "screen_capture")
    assert b1 == b2


def test_user_override_persists():
    from core.memory.bucket_classifier import classify_event, override_bucket
    event_id = str(uuid.uuid4())
    classify_event(event_id, "watched netflix", "screen_capture")
    override_bucket(event_id, "Creativity/Exploration")
    # Re-classify should return the override
    result = classify_event(event_id, "watched netflix", "screen_capture")
    assert result == "Creativity/Exploration"


# --- Graph ---

def test_add_and_retrieve_edge():
    from core.memory.graph import add_edge, get_neighbors
    add_edge("event-1", "person:abc123", edge_type="mentions", weight=1.0)
    neighbors = get_neighbors("event-1")
    assert any(n["node"] == "person:abc123" for n in neighbors)


def test_repeated_edges_accumulate_weight():
    from core.memory.graph import add_edge, get_neighbors
    add_edge("event-1", "person:abc123", edge_type="mentions", weight=1.0)
    add_edge("event-1", "person:abc123", edge_type="mentions", weight=1.0)
    neighbors = get_neighbors("event-1")
    match = next(n for n in neighbors if n["node"] == "person:abc123")
    assert match["weight"] == 2.0


def test_index_event_creates_person_edge():
    from core.memory.graph import index_event, get_neighbors
    event = _make_event("coffee with Alice")
    event["entities"] = [{"type": "PERSON", "hash": "a3f9b72c"}]
    event["bucket"] = "Relationships/Friends"
    index_event(event)
    neighbors = get_neighbors(event["id"])
    assert any("person:a3f9b72c" in n["node"] for n in neighbors)


def test_get_person_events():
    from core.memory.graph import index_event, get_person_events
    event = _make_event("dinner with Bob")
    event["entities"] = [{"type": "PERSON", "hash": "b00b1234"}]
    event["bucket"] = "Relationships/Friends"
    index_event(event)
    events = get_person_events("b00b1234")
    assert event["id"] in events


# --- Vector store (mocked embed to avoid needing Ollama in CI) ---

def test_add_and_search_chunks(monkeypatch):
    import core.memory.vector_store as vs
    # Mock embed to return a simple deterministic vector
    def fake_embed(text: str) -> list[float]:
        return [hash(text) % 100 / 100.0] * 64
    monkeypatch.setattr(vs, "embed", fake_embed)

    from core.memory.chunker import chunk_event
    event = _make_event("I went to the gym today for a great workout")
    chunks = chunk_event(event)
    vs.add_chunks(chunks)

    results = vs.search("workout gym", top_k=3)
    assert len(results) > 0
    assert results[0].event_id == event["id"]


def test_duplicate_chunks_not_added(monkeypatch):
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", lambda t: [0.1] * 64)

    from core.memory.chunker import chunk_event
    event = _make_event("duplicate test note")
    chunks = chunk_event(event)
    vs.add_chunks(chunks)
    vs.add_chunks(chunks)  # second call should be a no-op

    index = vs._load_index()
    keys = [(c.event_id, c.chunk_index) for c in index]
    assert len(keys) == len(set(keys))
