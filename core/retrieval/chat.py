from __future__ import annotations

from core.llm_service import chat as llm_chat
from core.memory.store import query
from core.retrieval.context_assembler import assemble, render_response

_SYSTEM_PROMPT = """\
You are a personal knowledge assistant with access to the user's captured notes, \
events, messages, and calendar. Answer based on the provided context. \
If the context doesn't contain enough information, say so directly. \
Be concise and conversational. Never reveal internal hash tokens — use them as-is in your response \
and they will be resolved automatically."""


def answer(user_query: str, top_k: int = 8, extra_context: str | None = None) -> str:
    """Full RAG pipeline: retrieve relevant chunks, assemble context, call LLM, render response."""
    chunks = query(user_query, top_k=top_k)
    context = assemble(chunks)

    hint_block = f"\n\n[Guidance for this response: {extra_context}]" if extra_context else ""
    prompt = (
        f"{_SYSTEM_PROMPT}{hint_block}"
        f"\n\nContext from your knowledge base:\n{context}"
        f"\n\nQuestion: {user_query}"
    )
    raw_response = llm_chat(prompt, context_entries=[])

    return render_response(raw_response)
