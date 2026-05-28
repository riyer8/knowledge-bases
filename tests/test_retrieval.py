"""Tests for core/retrieval/."""
from __future__ import annotations

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
    import core.memory.vector_store as vs
    import core.memory.store as st
    import core.retrieval.chat as chat_mod
    import core.retrieval.context_assembler as ca_mod
    for mod in (vs, st, chat_mod, ca_mod):
        reload(mod)
    yield tmp_path


def _fake_embed(text: str) -> list[float]:
    return [0.5] * 64


def test_answer_returns_string(monkeypatch):
    import core.memory.vector_store as vs
    import core.retrieval.chat as chat_mod
    monkeypatch.setattr(vs, "embed", _fake_embed)
    monkeypatch.setattr(chat_mod, "llm_chat", lambda prompt, context_entries: "Here is what I found.")

    from core.retrieval.chat import answer
    result = answer("what did I do yesterday?")
    assert isinstance(result, str)
    assert len(result) > 0


def test_answer_with_no_memory_still_returns(monkeypatch):
    import core.retrieval.chat as chat_mod
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", _fake_embed)
    monkeypatch.setattr(chat_mod, "llm_chat", lambda prompt, context_entries: "I don't have enough context.")

    from core.retrieval.chat import answer
    result = answer("what is my schedule?")
    assert isinstance(result, str)


def test_context_assembler_renders_chunks():
    from core.memory.vector_store import IndexedChunk
    from core.retrieval.context_assembler import assemble

    chunks = [
        IndexedChunk(
            event_id="e1", chunk_index=0,
            text="Went to the gym this morning.",
            source="screen_capture", timestamp="2026-05-27T08:00:00Z",
            flagged_important=False, sensitivity_score=0.1, vector=[],
        )
    ]
    context = assemble(chunks)
    assert "gym" in context
    assert "screen_capture" in context


def test_context_assembler_empty_chunks():
    from core.retrieval.context_assembler import assemble
    result = assemble([])
    assert "No relevant context" in result


def test_context_respects_token_budget():
    from core.memory.vector_store import IndexedChunk
    from core.retrieval.context_assembler import assemble

    # Create chunks that together exceed the budget
    big_text = "word " * 300
    chunks = [
        IndexedChunk(
            event_id=f"e{i}", chunk_index=0,
            text=big_text, source="screen_capture",
            timestamp="2026-05-27T08:00:00Z",
            flagged_important=False, sensitivity_score=0.1, vector=[],
        )
        for i in range(20)
    ]
    context = assemble(chunks, max_tokens=500)
    # Should be truncated — not all 20 chunks
    assert context.count("---") < 19


def test_render_response_resolves_hashes(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.privacy.hasher as hasher_mod
    reload(hasher_mod)
    import core.retrieval.context_assembler as ca_mod
    reload(ca_mod)

    import secrets
    hash_dir = tmp_path / "hashes"
    hash_dir.mkdir(parents=True)
    salt_path = hash_dir / "salt"
    salt_path.write_text(secrets.token_hex(32))
    salt_path.chmod(0o600)

    from core.privacy.hasher import get_or_create_hash
    h = get_or_create_hash("Alice")

    from core.retrieval.context_assembler import render_response
    rendered = render_response(f"You had coffee with [PERSON:{h}] yesterday.")
    assert "Alice" in rendered
    assert h not in rendered
