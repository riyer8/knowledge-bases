"""Tests for LLM provider abstraction."""
from __future__ import annotations

import pytest


def test_get_provider_defaults_to_ollama(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("KB_LLM_PROVIDER", "auto")
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.llm_providers as lp
    reload(lp)

    provider = lp.get_provider()
    assert provider.__class__.__name__ == "OllamaProvider"


def test_get_provider_auto_uses_openai_when_key_set(monkeypatch):
    monkeypatch.setenv("KB_LLM_PROVIDER", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.llm_providers as lp
    reload(lp)

    assert lp.resolve_llm_provider() == "openai"


def test_get_provider_openai(monkeypatch):
    monkeypatch.setenv("KB_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.llm_providers as lp
    reload(lp)

    provider = lp.get_provider()
    assert provider.__class__.__name__ == "OpenAIProvider"


def test_ollama_chat_non_stream(monkeypatch):
    monkeypatch.setenv("KB_LLM_PROVIDER", "ollama")
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.llm_providers as lp
    reload(lp)

    monkeypatch.setattr(lp, "_post_json", lambda url, payload, headers=None: {
        "message": {"content": "hello from ollama"}
    })
    result = lp.chat([{"role": "user", "content": "hi"}], stream=False)
    assert result == "hello from ollama"


def test_openai_embed_uses_sdk(monkeypatch):
    monkeypatch.setenv("KB_EMBED_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.llm_providers as lp
    reload(lp)

    class FakeEmbedding:
        def __init__(self, vector):
            self.embedding = vector

    class FakeResponse:
        data = [FakeEmbedding([0.1, 0.2, 0.3])]

    class FakeEmbeddings:
        def create(self, model, input):
            assert model == "text-embedding-3-small"
            return FakeResponse()

    class FakeClient:
        embeddings = FakeEmbeddings()

    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda api_key: FakeClient())
    result = lp.embed("hello world")
    assert result == [0.1, 0.2, 0.3]
