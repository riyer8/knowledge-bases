from __future__ import annotations

from core.memory.bucket_classifier import classify_event
from core.memory.chunker import chunk_event
from core.memory.graph import index_event
from core.memory.vector_store import add_chunks, search
from core.memory.vector_store import IndexedChunk


def ingest(event: dict) -> None:
    """
    Main entry point for the memory module.
    Takes a clean event (post-privacy) and:
    1. Classifies it into a life bucket
    2. Chunks and embeds it into the vector store
    3. Adds graph edges
    """
    event_id = event.get("id", "")
    text = event.get("content", {}).get("text", "")
    source = event.get("source", "unknown")

    if not text.strip():
        return

    capture = event.get("capture_context") or {}
    meta = (event.get("content") or {}).get("metadata") or {}
    url = str(capture.get("url") or meta.get("url") or "")

    # 1. Bucket classification
    bucket = classify_event(event_id, text, source, url=url)
    event["bucket"] = bucket

    # 2. Chunking + embedding
    chunks = chunk_event(event)
    add_chunks(chunks)

    # 3. Graph edges
    index_event(event)


def query(text: str, top_k: int = 8) -> list[IndexedChunk]:
    """Semantic search over the memory store."""
    return search(text, top_k=top_k)
