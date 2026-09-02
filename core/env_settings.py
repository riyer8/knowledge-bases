from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.config import config

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _REPO_ROOT / ".env"

_ALLOWED_KEYS = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "KB_LLM_PROVIDER",
    "OPENAI_MODEL",
    "KB_CHAT_MODEL",
    "KB_EMBED_MODEL",
    "KB_EMBED_PROVIDER",
    "KB_PROACTIVE_INTERVAL_MINUTES",
}


def env_file_path() -> Path:
    return _ENV_PATH


def _mask_secret(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) <= 8:
        return "••••"
    return f"{value[:3]}…{value[-4:]}"


def _reload_config_from_env() -> None:
    load_dotenv(_ENV_PATH, override=True)
    config.llm_provider = os.environ.get("KB_LLM_PROVIDER", config.llm_provider)
    config.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    config.openai_model = os.environ.get("OPENAI_MODEL", config.openai_model)
    config.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    config.anthropic_model = os.environ.get("ANTHROPIC_MODEL", config.anthropic_model)
    config.chat_model = os.environ.get("KB_CHAT_MODEL", config.chat_model)
    config.embed_model = os.environ.get("KB_EMBED_MODEL", config.embed_model)
    config.embed_provider = os.environ.get("KB_EMBED_PROVIDER", config.embed_provider)
    if os.environ.get("KB_PROACTIVE_INTERVAL_MINUTES"):
        config.proactive_interval_minutes = int(os.environ["KB_PROACTIVE_INTERVAL_MINUTES"])


def get_client_settings() -> dict[str, Any]:
    from core.llm_providers import resolve_llm_provider

    provider = resolve_llm_provider()
    ollama_needed = provider == "ollama"
    return {
        "env_path": str(_ENV_PATH),
        "env_exists": _ENV_PATH.exists(),
        "kb_root": str(config.kb_root),
        "backend_port": config.backend_port,
        "llm_provider": provider,
        "llm_provider_setting": config.llm_provider,
        "chat_model": config.chat_model,
        "embed_provider": config.embed_provider,
        "embed_model": config.embed_model,
        "openai_model": config.openai_model,
        "proactive_interval_minutes": config.proactive_interval_minutes,
        "openai_configured": bool(config.openai_api_key),
        "openai_key_hint": _mask_secret(config.openai_api_key),
        "anthropic_configured": bool(config.anthropic_api_key),
        "anthropic_key_hint": _mask_secret(config.anthropic_api_key),
        "ollama_required": ollama_needed,
        "setup_notes": _setup_notes(provider, ollama_needed),
    }


def _setup_notes(provider: str, ollama_needed: bool) -> list[str]:
    notes = [
        "All data stays on this Mac in ~/.kb/ unless you delete it.",
        "Run the launcher once so the backend can start automatically.",
    ]
    if ollama_needed:
        notes.append("Start Ollama (ollama serve) and pull the chat + embed models listed below.")
    elif provider == "openai":
        notes.append("OpenAI is active — chat and embeddings use your API key.")
    elif provider == "anthropic":
        notes.append("Anthropic is active for chat; embeddings may still use OpenAI or Ollama.")
    return notes


def update_client_settings(payload: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, str] = {}

    if "llm_provider" in payload:
        value = str(payload.get("llm_provider", "")).strip().lower()
        if value not in {"auto", "ollama", "openai", "anthropic"}:
            raise ValueError("llm_provider must be auto, ollama, openai, or anthropic")
        updates["KB_LLM_PROVIDER"] = value

    if "openai_api_key" in payload:
        updates["OPENAI_API_KEY"] = str(payload.get("openai_api_key", "")).strip()

    if "anthropic_api_key" in payload:
        updates["ANTHROPIC_API_KEY"] = str(payload.get("anthropic_api_key", "")).strip()

    if "chat_model" in payload:
        value = str(payload.get("chat_model", "")).strip()
        if value:
            updates["KB_CHAT_MODEL"] = value

    if "openai_model" in payload:
        value = str(payload.get("openai_model", "")).strip()
        if value:
            updates["OPENAI_MODEL"] = value

    if "embed_provider" in payload:
        value = str(payload.get("embed_provider", "")).strip().lower()
        if value not in {"auto", "ollama", "openai"}:
            raise ValueError("embed_provider must be auto, ollama, or openai")
        updates["KB_EMBED_PROVIDER"] = value

    if "proactive_interval_minutes" in payload:
        minutes = int(payload.get("proactive_interval_minutes", 20))
        if minutes < 5 or minutes > 240:
            raise ValueError("proactive_interval_minutes must be between 5 and 240")
        updates["KB_PROACTIVE_INTERVAL_MINUTES"] = str(minutes)

    if not updates:
        raise ValueError("no settings to update")

    _write_env_updates(updates)
    _reload_config_from_env()
    return get_client_settings()


def _write_env_updates(updates: dict[str, str]) -> None:
    for key in updates:
        if key not in _ALLOWED_KEYS:
            raise ValueError(f"unsupported setting: {key}")

    if not _ENV_PATH.exists():
        example = _REPO_ROOT / ".env.example"
        if example.exists():
            _ENV_PATH.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            _ENV_PATH.write_text("", encoding="utf-8")

    lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    new_lines: list[str] = []

    key_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
    for line in lines:
        match = key_pattern.match(line.strip())
        if match:
            key = match.group(1)
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        new_lines.append(line)

    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={value}")

    _ENV_PATH.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
