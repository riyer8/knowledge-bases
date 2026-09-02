from __future__ import annotations

from pathlib import Path


def test_update_env_file_creates_and_updates(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    example = tmp_path / ".env.example"
    example.write_text("KB_LLM_PROVIDER=auto\nOPENAI_API_KEY=\n", encoding="utf-8")

    monkeypatch.setattr("core.env_settings._ENV_PATH", env_file)
    monkeypatch.setattr("core.env_settings._REPO_ROOT", tmp_path)

    from core.env_settings import get_client_settings, update_client_settings

    settings = update_client_settings({
        "llm_provider": "openai",
        "openai_api_key": "sk-test-abcdef",
        "openai_model": "gpt-4o-mini",
    })
    assert settings["openai_configured"] is True
    assert "sk-…cdef" in settings["openai_key_hint"]

    text = env_file.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=sk-test-abcdef" in text
    assert "KB_LLM_PROVIDER=openai" in text

    status = get_client_settings()
    assert status["llm_provider_setting"] == "openai"
