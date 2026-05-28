from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from core.config import config
from core.llm_service import embed
from core.memory.chunker import Chunk


@dataclass
class IndexedChunk:
    event_id: str
    chunk_index: int
    text: str
    source: str
    timestamp: str
    flagged_important: bool
    sensitivity_score: float
    vector: list[float]


def _index_path() -> Path:
    return config.index_dir / "chunks.json"


def _load_index() -> list[IndexedChunk]:
    path = _index_path()
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [IndexedChunk(**entry) for entry in raw]


def _save_index(chunks: list[IndexedChunk]) -> None:
    config.index_dir.mkdir(parents=True, exist_ok=True)
    _index_path().write_text(json.dumps([asdict(c) for c in chunks], indent=2))


def add_chunks(chunks: list[Chunk]) -> None:
    """Embed and persist a list of chunks to the vector store."""
    existing = _load_index()
    existing_keys = {(c.event_id, c.chunk_index) for c in existing}

    new_entries: list[IndexedChunk] = []
    for chunk in chunks:
        if (chunk.event_id, chunk.chunk_index) in existing_keys:
            continue
        vector = embed(chunk.text)
        new_entries.append(IndexedChunk(
            event_id=chunk.event_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            source=chunk.source,
            timestamp=chunk.timestamp,
            flagged_important=chunk.flagged_important,
            sensitivity_score=chunk.sensitivity_score,
            vector=vector,
        ))

    if new_entries:
        _save_index(existing + new_entries)


def search(query: str, top_k: int = 8) -> list[IndexedChunk]:
    """Return the top-k most semantically similar chunks for a query."""
    index = _load_index()
    if not index:
        return []

    query_vec = embed(query)
    if not query_vec:
        return []

    scored = [(chunk, _cosine(query_vec, chunk.vector)) for chunk in index if chunk.vector]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in scored[:top_k]]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
