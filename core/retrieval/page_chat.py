from __future__ import annotations

from collections.abc import Iterator

from core.llm_providers import chat as provider_chat
from core.memory.concept_graph import related_for_page
from core.page_context_service import get_connections, render_page_context, touch_page
from core.retrieval.context_assembler import render_response

_SYSTEM_PROMPT = """\
You are Context, a personal reading assistant that remembers what the user has learned.

You can explain pages, connect ideas to prior reading, quiz the user, find gaps, \
suggest what to explore next, and help them think clearly.

Be concise, specific, and helpful. If the user asks to be quizzed, actually quiz them \
with questions and wait for answers. If evidence is missing, say so directly."""


def _build_messages(
    question: str,
    page: dict,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    page_block = render_page_context(page)
    connections = get_connections(url=page.get("url", ""), query=question, top_k=5)
    concepts = related_for_page(page_url=page.get("url", ""), query=question, limit=5)

    blocks: list[str] = [f"Current page:\n{page_block}"]
    if concepts:
        lines = [f"- {c.get('name')}" for c in concepts]
        blocks.append("Known concepts:\n" + "\n".join(lines))
    if connections:
        lines = []
        for item in connections[:5]:
            label = item.get("title") or item.get("name") or "prior reading"
            lines.append(f"- {label}: {item.get('text', '')[:250]}")
        blocks.append("Related memory:\n" + "\n".join(lines))

    user_content = "\n\n".join(blocks) + f"\n\nQuestion: {question}"

    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for turn in history or []:
        role = str(turn.get("role", "")).strip()
        content = str(turn.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_content})
    return messages


def ask_about_page(
    question: str,
    page: dict,
    *,
    history: list[dict[str, str]] | None = None,
    stream: bool = False,
    saved_page_id: str = "",
) -> str | Iterator[str]:
    messages = _build_messages(question, page, history)
    if saved_page_id:
        from core.library_service import append_chat_turn
        append_chat_turn(saved_page_id, "user", question)
    elif page.get("id"):
        touch_page(str(page["id"]))

    result = provider_chat(messages, stream=stream)
    if stream:
        return _stream_with_render(result, saved_page_id)  # type: ignore[arg-type]
    reply = render_response(str(result))
    if saved_page_id:
        from core.library_service import append_chat_turn
        append_chat_turn(saved_page_id, "assistant", reply)
    return reply


def _stream_with_render(chunks: Iterator[str], saved_page_id: str = "") -> Iterator[str]:
    collected: list[str] = []
    for token in chunks:
        collected.append(token)
        yield token
    if saved_page_id:
        from core.library_service import append_chat_turn
        append_chat_turn(saved_page_id, "assistant", "".join(collected))
