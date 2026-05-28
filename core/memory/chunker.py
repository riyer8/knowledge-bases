from __future__ import annotations

from dataclasses import dataclass

_CHUNK_SIZE = 400   # characters
_CHUNK_OVERLAP = 80


@dataclass
class Chunk:
    event_id: str
    chunk_index: int
    text: str
    source: str
    timestamp: str
    flagged_important: bool
    sensitivity_score: float


def chunk_event(event: dict) -> list[Chunk]:
    """
    Split a clean event into overlapping text chunks ready for embedding.
    Short events produce a single chunk.
    """
    text: str = event.get("content", {}).get("text", "").strip()
    if not text:
        return []

    event_id: str = event["id"]
    source: str = event.get("source", "unknown")
    timestamp: str = event.get("timestamp", "")
    flagged: bool = event.get("flagged_important", False)
    sensitivity: float = float(event.get("sensitivity_score", 0.0))

    if len(text) <= _CHUNK_SIZE:
        return [Chunk(
            event_id=event_id,
            chunk_index=0,
            text=text,
            source=source,
            timestamp=timestamp,
            flagged_important=flagged,
            sensitivity_score=sensitivity,
        )]

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + _CHUNK_SIZE
        chunk_text = text[start:end]
        chunks.append(Chunk(
            event_id=event_id,
            chunk_index=idx,
            text=chunk_text,
            source=source,
            timestamp=timestamp,
            flagged_important=flagged,
            sensitivity_score=sensitivity,
        ))
        start += _CHUNK_SIZE - _CHUNK_OVERLAP
        idx += 1

    return chunks
