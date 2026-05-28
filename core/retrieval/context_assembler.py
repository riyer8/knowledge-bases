from __future__ import annotations

from core.memory.vector_store import IndexedChunk
from core.privacy.hasher import resolve_hash
import re

_HASH_RE = re.compile(r"\[PERSON:([a-f0-9]{8})\]")


def _render_names(text: str) -> str:
    """Replace [PERSON:hash] tokens with display names for the user-facing response."""
    def replace(match: re.Match) -> str:
        display = resolve_hash(match.group(1))
        return display if display else match.group(0)
    return _HASH_RE.sub(replace, text)


def assemble(chunks: list[IndexedChunk], max_tokens: int = 2000) -> str:
    """
    Build a context string from retrieved chunks to include in the LLM prompt.
    Chunks are ordered by relevance (already ranked by caller).
    Names are kept as hashes — the LLM never sees real names.
    """
    if not chunks:
        return "No relevant context found."

    parts: list[str] = []
    total_chars = 0
    char_budget = max_tokens * 4  # rough chars-per-token estimate

    for chunk in chunks:
        entry = f"[{chunk.source} · {chunk.timestamp[:10]}]\n{chunk.text}"
        if total_chars + len(entry) > char_budget:
            break
        parts.append(entry)
        total_chars += len(entry)

    return "\n\n---\n\n".join(parts)


def render_response(text: str) -> str:
    """Post-process LLM response: replace hashes with display names before showing user."""
    return _render_names(text)
