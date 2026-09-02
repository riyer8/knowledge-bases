from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any
from urllib import error, request

from core.config import config

OLLAMA_BASE_URL = "http://localhost:11434"
OPENAI_BASE_URL = "https://api.openai.com/v1"
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
        max_tokens: int | None = None,
    ) -> str | Iterator[str]:
        """Return full text or stream token chunks."""


class OllamaProvider(LLMProvider):
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
        max_tokens: int | None = None,
    ) -> str | Iterator[str]:
        payload = {
            "model": config.chat_model,
            "stream": stream,
            "messages": messages,
        }
        if stream:
            return self._stream_ollama(payload)
        return _extract_ollama_content(_post_json(f"{OLLAMA_BASE_URL}/api/chat", payload))

    def _stream_ollama(self, payload: dict[str, Any]) -> Iterator[str]:
        req = request.Request(
            f"{OLLAMA_BASE_URL}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except error.URLError as exc:
            raise RuntimeError(
                f"Ollama not reachable at {OLLAMA_BASE_URL}. Is it running? (`ollama serve`)\n{exc}"
            ) from exc


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        if not config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        self._client = OpenAI(api_key=config.openai_api_key)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
        max_tokens: int | None = None,
    ) -> str | Iterator[str]:
        if stream:
            return self._stream_openai(messages, max_tokens=max_tokens)
        kwargs: dict[str, Any] = {
            "model": config.openai_model,
            "messages": messages,
            "stream": False,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        def _create() -> str:
            response = self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""

        return _call_openai_with_retry(_create)

    def _stream_openai(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        kwargs: dict[str, Any] = {
            "model": config.openai_model,
            "messages": messages,
            "stream": True,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        def _open_stream():
            return self._client.chat.completions.create(**kwargs)

        stream = _call_openai_with_retry(_open_stream)
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield token


class AnthropicProvider(LLMProvider):
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
        max_tokens: int | None = None,
    ) -> str | Iterator[str]:
        if not config.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_messages = [m for m in messages if m["role"] != "system"]
        payload = {
            "model": config.anthropic_model,
            "max_tokens": max_tokens or 4096,
            "system": "\n\n".join(system_parts) if system_parts else "",
            "messages": user_messages,
            "stream": stream,
        }
        headers = {
            "content-type": "application/json",
            "x-api-key": config.anthropic_api_key,
            "anthropic-version": "2023-06-01",
        }
        if stream:
            return self._stream_anthropic(payload, headers)
        body = _post_json(f"{ANTHROPIC_BASE_URL}/messages", payload, headers=headers)
        parts = body.get("content", [])
        return "".join(part.get("text", "") for part in parts if part.get("type") == "text")

    def _stream_anthropic(self, payload: dict[str, Any], headers: dict[str, str]) -> Iterator[str]:
        req = request.Request(
            f"{ANTHROPIC_BASE_URL}/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                if chunk.get("type") == "content_block_delta":
                    token = chunk.get("delta", {}).get("text", "")
                    if token:
                        yield token


def resolve_llm_provider() -> str:
    provider = config.llm_provider.lower().strip()
    if provider == "auto":
        if config.openai_api_key:
            return "openai"
        return "ollama"
    return provider


def resolve_embed_provider() -> str:
    provider = config.embed_provider.lower().strip()
    if provider == "auto":
        if config.openai_api_key:
            return "openai"
        return "ollama"
    return provider


def get_provider() -> LLMProvider:
    provider = resolve_llm_provider()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "anthropic":
        return AnthropicProvider()
    return OllamaProvider()


def chat(
    messages: list[dict[str, str]],
    *,
    stream: bool = False,
    max_tokens: int | None = None,
) -> str | Iterator[str]:
    return get_provider().chat(messages, stream=stream, max_tokens=max_tokens)


def embed(text: str) -> list[float]:
    """Generate an embedding vector using OpenAI or Ollama."""
    provider = resolve_embed_provider()
    if provider == "openai":
        if not config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        client = OpenAI(api_key=config.openai_api_key)

        def _create() -> list[float]:
            response = client.embeddings.create(
                model=config.openai_embed_model,
                input=text,
            )
            return list(response.data[0].embedding)

        return _call_openai_with_retry(_create)

    payload = {"model": config.embed_model, "input": text}
    result = _post_json(f"{OLLAMA_BASE_URL}/api/embed", payload)
    embeddings = result.get("embeddings", [])
    if isinstance(embeddings, list) and embeddings:
        return embeddings[0]
    return []


def _retry_seconds_from_error(exc: Exception) -> int | None:
    match = re.search(r"try again in (\d+)s", str(exc), re.I)
    if match:
        return int(match.group(1)) + 1
    return None


def _friendly_llm_error(exc: Exception) -> str:
    message = str(exc)
    if "rate_limit" in message.lower() or "429" in message:
        wait = _retry_seconds_from_error(exc) or 10
        return (
            f"OpenAI rate limit reached — wait about {wait}s and try again, "
            "or switch to Ollama in Settings."
        )
    return message


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    if "rate_limit" in message or "429" in message:
        return True
    status = getattr(exc, "status_code", None)
    return status == 429


def _call_openai_with_retry(call, *, max_attempts: int = 3):
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return call()
        except Exception as exc:
            if not _is_rate_limit_error(exc):
                raise
            last_exc = exc
            if attempt >= max_attempts - 1:
                break
            wait = _retry_seconds_from_error(exc) or (attempt + 1) * 5
            time.sleep(wait)
    raise RuntimeError(_friendly_llm_error(last_exc or RuntimeError("LLM request failed")))


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    req_headers = {"content-type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=req_headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LLM request failed ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc


def _extract_ollama_content(body: dict[str, Any]) -> str:
    message = body.get("message", {})
    return str(message.get("content", ""))
