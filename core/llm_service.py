from __future__ import annotations

import json
from pathlib import Path
from urllib import error, request

from core.config import config
from core.llm_providers import chat as provider_chat, embed as provider_embed

OLLAMA_BASE_URL = "http://localhost:11434"
PROMPT_PATH = Path(__file__).resolve().parent / "chat_prompt.txt"


def _load_system_prompt() -> str:
    if PROMPT_PATH.exists():
        text = PROMPT_PATH.read_text(encoding="utf-8").strip()
        if text:
            return text
    return (
        "You are a personal knowledge assistant. You have access to the user's "
        "notes, events, and captured context. Answer concisely and helpfully."
    )


def _build_context_block(entries: list[dict]) -> str:
    recent = entries[:5]
    if not recent:
        return "No context available."
    lines = [f"{i}. [{e.get('kind', 'note')}] {e.get('value', '')}" for i, e in enumerate(recent, 1)]
    return "\n".join(lines)


def chat(prompt: str, context_entries: list[dict] | None = None) -> str:
    """Send a chat message to the configured LLM provider and return the response."""
    entries = context_entries or []
    context = _build_context_block(entries)
    system = _load_system_prompt()

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"{prompt}\n\nContext:\n{context}",
        },
    ]
    result = provider_chat(messages, stream=False)
    return str(result)


def embed(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    return provider_embed(text)


def classify(text: str, categories: list[str]) -> str:
    """Ask the configured LLM to classify text into one of the provided categories."""
    cats = ", ".join(categories)
    messages = [
        {
            "role": "user",
            "content": (
                f"Classify the following text into exactly one of these categories: {cats}.\n"
                f"Reply with only the category name, nothing else.\n\nText: {text}"
            ),
        }
    ]
    return str(provider_chat(messages, stream=False)).strip()


def _post_ollama(path: str, payload: dict, response_key: str) -> any:
    url = OLLAMA_BASE_URL + path
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(
            f"Ollama not reachable at {OLLAMA_BASE_URL}. Is it running? (`ollama serve`)\n{exc}"
        ) from exc

    # Traverse dot-separated key path
    result = body
    for key in response_key.split("."):
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return result
    return result
