"""Tests for core/integrations/. Mocks all network calls."""
from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    monkeypatch.setenv("KB_GCAL_CLIENT_ID", "test-gcal-client-id")
    monkeypatch.setenv("KB_GCAL_CLIENT_SECRET", "test-gcal-secret")
    monkeypatch.setenv("KB_GMAIL_CLIENT_ID", "test-gmail-client-id")
    monkeypatch.setenv("KB_GMAIL_CLIENT_SECRET", "test-gmail-secret")
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.integrations.oauth as oauth_mod
    import core.integrations.gcal as gcal_mod
    import core.integrations.gmail as gmail_mod
    for mod in (oauth_mod, gcal_mod, gmail_mod):
        reload(mod)
    yield tmp_path


# --- OAuth helpers ---

def test_save_and_load_token(tmp_path):
    from core.integrations.oauth import save_token, load_token
    token = {"access_token": "abc", "refresh_token": "xyz", "expires_at": time.time() + 3600}
    save_token("gcal", token)
    loaded = load_token("gcal")
    assert loaded["access_token"] == "abc"


def test_token_file_permissions(tmp_path):
    from core.integrations.oauth import save_token, token_path
    save_token("gcal", {"access_token": "test", "expires_at": time.time() + 3600})
    path = token_path("gcal")
    mode = oct(path.stat().st_mode)[-3:]
    assert mode == "600"


def test_is_expired_true():
    from core.integrations.oauth import is_expired
    token = {"expires_at": time.time() - 100}
    assert is_expired(token) is True


def test_is_expired_false():
    from core.integrations.oauth import is_expired
    token = {"expires_at": time.time() + 3600}
    assert is_expired(token) is False


def test_build_auth_url_contains_client_id():
    from core.integrations.oauth import build_auth_url
    url = build_auth_url("my-client-id", ["scope1"], "http://redirect", state="test")
    assert "my-client-id" in url
    assert "scope1" in url
    assert "offline" in url


def test_load_token_returns_none_when_missing(tmp_path):
    from core.integrations.oauth import load_token
    assert load_token("nonexistent") is None


# --- GCal ---

def test_gcal_auth_url_contains_google():
    from core.integrations.gcal import auth_url
    url = auth_url()
    assert "accounts.google.com" in url
    assert "calendar" in url


def test_gcal_sync_ingests_events(tmp_path, monkeypatch):
    import core.integrations.gcal as gcal_mod
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", lambda t: [0.1] * 64)

    fake_events = {
        "items": [
            {
                "id": "evt1",
                "summary": "Team standup",
                "status": "confirmed",
                "start": {"dateTime": "2026-05-27T09:00:00Z"},
                "end": {"dateTime": "2026-05-27T09:30:00Z"},
                "attendees": [{"email": "alice@example.com", "displayName": "Alice"}],
            },
            {
                "id": "evt2",
                "summary": "Cancelled event",
                "status": "cancelled",
                "start": {"dateTime": "2026-05-27T10:00:00Z"},
                "end": {"dateTime": "2026-05-27T11:00:00Z"},
            },
        ]
    }

    from core.integrations.oauth import save_token
    save_token("gcal", {"access_token": "test-token", "expires_at": time.time() + 3600})

    monkeypatch.setattr(gcal_mod, "_api_get", lambda path, params=None: fake_events)

    from core.integrations.gcal import sync
    count = sync()
    assert count == 1  # cancelled event skipped


def test_gcal_sync_skips_cancelled(tmp_path, monkeypatch):
    import core.integrations.gcal as gcal_mod
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", lambda t: [0.1] * 64)

    from core.integrations.oauth import save_token
    save_token("gcal", {"access_token": "test-token", "expires_at": time.time() + 3600})

    monkeypatch.setattr(gcal_mod, "_api_get", lambda path, params=None: {
        "items": [{"id": "e1", "status": "cancelled", "summary": "Gone",
                   "start": {"dateTime": "2026-05-27T09:00:00Z"},
                   "end": {"dateTime": "2026-05-27T10:00:00Z"}}]
    })

    from core.integrations.gcal import sync
    assert sync() == 0


# --- Gmail ---

def test_gmail_auth_url_contains_google():
    from core.integrations.gmail import auth_url
    url = auth_url()
    assert "accounts.google.com" in url
    assert "gmail" in url


def test_gmail_sync_ingests_threads(tmp_path, monkeypatch):
    import core.integrations.gmail as gmail_mod
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", lambda t: [0.1] * 64)

    from core.integrations.oauth import save_token
    save_token("gmail", {"access_token": "test-token", "expires_at": time.time() + 3600})

    thread_list = {"threads": [{"id": "thread1"}, {"id": "thread2"}]}
    thread_detail = {
        "id": "thread1",
        "messages": [{
            "id": "msg1",
            "labelIds": ["INBOX"],
            "snippet": "Hey, let's catch up soon",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Catch up"},
                    {"name": "From", "value": "bob@example.com"},
                    {"name": "Date", "value": "Mon, 27 May 2026 10:00:00 +0000"},
                ]
            }
        }]
    }

    call_count = {"n": 0}
    def fake_api_get(path, params=None):
        call_count["n"] += 1
        if "threads" in path and "/" not in path.replace("/users/me/threads", ""):
            return thread_list
        return thread_detail

    monkeypatch.setattr(gmail_mod, "_api_get", fake_api_get)

    from core.integrations.gmail import sync
    count = sync()
    assert count == 2


def test_get_pending_threads_filters_replied(tmp_path, monkeypatch):
    import core.integrations.gmail as gmail_mod

    from core.integrations.oauth import save_token
    save_token("gmail", {"access_token": "test-token", "expires_at": time.time() + 3600})

    thread_list = {"threads": [{"id": "thread_unreplied"}, {"id": "thread_replied"}]}

    def fake_api_get(path, params=None):
        if "thread_replied" in path:
            return {
                "id": "thread_replied",
                "messages": [
                    {"id": "m1", "labelIds": ["INBOX"], "snippet": "hi",
                     "payload": {"headers": [
                         {"name": "Subject", "value": "Test"},
                         {"name": "From", "value": "alice@example.com"},
                         {"name": "Date", "value": "Mon, 27 May 2026"},
                     ]}},
                    {"id": "m2", "labelIds": ["SENT"], "snippet": "reply",
                     "payload": {"headers": []}},
                ]
            }
        if "thread_unreplied" in path:
            return {
                "id": "thread_unreplied",
                "messages": [
                    {"id": "m3", "labelIds": ["INBOX"], "snippet": "hey",
                     "payload": {"headers": [
                         {"name": "Subject", "value": "Pending"},
                         {"name": "From", "value": "carol@example.com"},
                         {"name": "Date", "value": "Mon, 27 May 2026"},
                     ]}},
                ]
            }
        return thread_list

    monkeypatch.setattr(gmail_mod, "_api_get", fake_api_get)

    from core.integrations.gmail import get_pending_threads
    pending = get_pending_threads()
    assert len(pending) == 1
    assert pending[0]["thread_id"] == "thread_unreplied"
