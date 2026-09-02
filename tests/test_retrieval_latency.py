"""Retrieval latency regression gate (see docs/testing.md)."""
from __future__ import annotations

import time

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.memory.vector_store as vs_mod
    import core.memory.store as st_mod
    reload(vs_mod)
    reload(st_mod)
    cfg_mod.config.ensure_dirs()
    yield tmp_path


def _fake_embed(text: str) -> list[float]:
    # Deterministic 64-dim vector from text hash
    seed = sum(ord(c) for c in text) % 1000
    return [((seed + i) % 100) / 100.0 for i in range(64)]


def _seed_index(count: int = 120) -> None:
    from core.memory.chunker import Chunk
    from core.memory.vector_store import add_chunks

    chunks = [
        Chunk(
            event_id=f"evt-{i}",
            chunk_index=0,
            text=f"Captured note about topic {i % 20} with some context.",
            source="manual_text",
            timestamp="2026-05-27T08:00:00Z",
            flagged_important=False,
            sensitivity_score=0.1,
        )
        for i in range(count)
    ]
    add_chunks(chunks)


def test_query_p95_latency_under_2_seconds(monkeypatch):
    import core.memory.vector_store as vs_mod

    monkeypatch.setattr(vs_mod, "embed", _fake_embed)
    _seed_index(120)

    from core.memory.store import query

    samples = 20
    durations: list[float] = []
    for i in range(samples):
        start = time.perf_counter()
        results = query(f"what happened with topic {i % 10}", top_k=8)
        durations.append(time.perf_counter() - start)
        assert isinstance(results, list)

    durations.sort()
    p95_index = max(0, int(len(durations) * 0.95) - 1)
    p95 = durations[p95_index]
    assert p95 < 2.0, f"p95 latency {p95:.3f}s exceeds 2s budget"
