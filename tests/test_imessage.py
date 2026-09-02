"""Tests for core/integrations/imessage.py."""
from __future__ import annotations

import pytest


def test_is_available_false_when_not_darwin(monkeypatch):
    monkeypatch.setattr("core.integrations.imessage.platform.system", lambda: "Linux")
    from importlib import reload
    import core.integrations.imessage as im
    reload(im)
    assert im.is_available() is False


def test_fetch_recent_returns_empty_when_unavailable(monkeypatch):
    monkeypatch.setattr("core.integrations.imessage.is_available", lambda: False)
    from core.integrations.imessage import fetch_recent

    assert fetch_recent() == []


def test_ingest_recent_noop_when_unavailable(monkeypatch):
    monkeypatch.setattr("core.integrations.imessage.fetch_recent", lambda limit=30: [])
    monkeypatch.setattr("core.integrations.imessage.is_available", lambda: False)
    from core.integrations.imessage import ingest_recent

    result = ingest_recent(limit=5)
    assert result == {"ok": True, "ingested": 0, "available": False}


def test_ingest_recent_calls_pipeline(monkeypatch, tmp_path):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    cfg_mod.config.ensure_dirs()

    captured: list[str] = []

    def fake_ingest(text, source="manual_text", metadata=None, flagged_important=False):
        captured.append(text)

    monkeypatch.setattr("core.integrations.imessage.ingest_text", fake_ingest)
    monkeypatch.setattr(
        "core.integrations.imessage.fetch_recent",
        lambda limit=30: [{
            "message_id": "1",
            "handle": "+15551234",
            "direction": "received",
            "text_preview": "Hello there",
            "timestamp": "2026-05-27T12:00:00+00:00",
        }],
    )
    monkeypatch.setattr("core.integrations.imessage.is_available", lambda: True)

    from core.integrations.imessage import ingest_recent

    result = ingest_recent(limit=1)
    assert result["ingested"] == 1
    assert len(captured) == 1
    assert "Hello there" in captured[0]
