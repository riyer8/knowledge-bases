from __future__ import annotations

from collections.abc import Iterator

from core.llm_providers import chat as provider_chat
from core.memory.store import query
from core.retrieval.context_assembler import assemble, render_response
from core.retrieval.time_context import calendar_context_block

_SYSTEM_PROMPT = """\
You are a personal knowledge assistant with access to the user's captured notes, \
events, messages, and calendar. Answer based on the provided context. \
If the context doesn't contain enough information, say so directly. \
Be concise and conversational. Never reveal internal hash tokens — use them as-is in your response \
and they will be resolved automatically."""


def answer(
    user_query: str,
    *,
    top_k: int = 8,
    extra_context: str | None = None,
    history: list[dict[str, str]] | None = None,
    include_calendar: bool = True,
) -> str:
    """Full RAG pipeline with optional conversation history and calendar context."""
    chunks = query(user_query, top_k=top_k)
    context = assemble(chunks)

    hints: list[str] = []
    if include_calendar:
        cal = calendar_context_block()
        if cal:
            hints.append(cal)
    if extra_context:
        hints.append(extra_context)

    hint_block = ""
    if hints:
        hint_block = "\n\n[Context hints]\n" + "\n\n".join(hints)

    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for turn in history or []:
        role = str(turn.get("role", "")).strip()
        content = str(turn.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    user_content = (
        f"Knowledge base context:\n{context}{hint_block}\n\nQuestion: {user_query}"
    )
    messages.append({"role": "user", "content": user_content})

    raw_response = provider_chat(messages, stream=False)
    return render_response(str(raw_response))
