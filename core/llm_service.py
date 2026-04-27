from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import error, request

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
PROMPT_PATH = REPO_ROOT / "core" / "chat_prompt.txt"


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#") or "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def load_system_prompt() -> str:
    if PROMPT_PATH.exists():
        text = PROMPT_PATH.read_text(encoding="utf-8").strip()
        if text:
            return text
    return (
        "You are a concise assistant for a desktop pet app. "
        "Use recent manual inputs as context when useful."
    )


def build_context_block(entries: list[dict]) -> str:
    recent = entries[:5]
    if not recent:
        return "No manual inputs are saved yet."
    lines: list[str] = []
    for idx, item in enumerate(recent, start=1):
        kind = item.get("kind", "unknown")
        value = str(item.get("value", ""))
        lines.append(f"{idx}. [{kind}] {value}")
    return "\n".join(lines)


def fallback_chat_reply(prompt: str, entries: list[dict]) -> str:
    context = build_context_block(entries)
    return (
        "Claude API key is not configured yet.\n\n"
        f"Prompt received: {prompt}\n\n"
        "To enable live responses, set `CLAUDE_CODE_API_KEY` in `.env` and restart the backend.\n\n"
        f"Recent manual inputs:\n{context}"
    )


def call_claude_chat(prompt: str, entries: list[dict]) -> str:
    load_dotenv()
    api_key = os.getenv("CLAUDE_CODE_API_KEY", "").strip()
    if not api_key or api_key.lower().startswith("replace"):
        return fallback_chat_reply(prompt, entries)

    model = os.getenv("CLAUDE_CODE_MODEL", "claude-3-5-sonnet-latest").strip()
    context = build_context_block(entries)
    payload = {
        "model": model,
        "max_tokens": 600,
        "system": load_system_prompt(),
        "messages": [
            {
                "role": "user",
                "content": (
                    f"User prompt:\n{prompt}\n\n"
                    f"Recent manual input context:\n{context}\n\n"
                    "Respond helpfully for the desktop app chat UI."
                ),
            }
        ],
    }
    req = request.Request(
        CLAUDE_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return f"Claude API request failed ({exc.code}). {details[:260]}"
    except Exception as exc:
        return f"Claude API call error: {exc}"

    for block in parsed.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            text = str(block.get("text", "")).strip()
            if text:
                return text
    return "Claude returned an empty response."
