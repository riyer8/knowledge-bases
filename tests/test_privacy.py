"""
Tests for core/privacy/. Run with: pytest tests/test_privacy.py
Requires: pip install spacy && python -m spacy download en_core_web_sm
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    """Each test gets its own kb_root so hash maps don't bleed between tests."""
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    # Reload all privacy submodules so they pick up the new config
    import core.privacy.hasher as hasher_mod
    import core.privacy.pipeline as pipeline_mod
    reload(hasher_mod)
    reload(pipeline_mod)
    yield tmp_path


# --- Pause detection ---

def test_banking_url_triggers_pause():
    from core.privacy.pipeline import process
    result = process("my balance is $500", source="screen_capture", url="https://chase.com/dashboard")
    assert result["should_pause"] is True
    assert result["text"] == ""


def test_password_window_title_triggers_pause():
    from core.privacy.pipeline import process
    result = process("hunter2", source="screen_capture", window_title="Enter Password — System")
    assert result["should_pause"] is True
    assert result["text"] == ""


def test_credential_app_triggers_pause():
    from core.privacy.pipeline import process
    result = process("my secret", source="screen_capture", app_name="1Password")
    assert result["should_pause"] is True


def test_paused_event_logs_metadata(tmp_path):
    from core.privacy.pipeline import process
    process("secret", source="screen_capture", url="https://bankofamerica.com/login")
    log_path = tmp_path / "events" / "paused.log"
    assert log_path.exists()
    content = log_path.read_text()
    assert "paused" in content
    # Must not contain the actual text
    assert "secret" not in content


def test_normal_content_does_not_pause():
    from core.privacy.pipeline import process
    result = process("I read a great article today", source="screen_capture")
    assert result["should_pause"] is False


# --- Name hashing ---

def test_person_name_is_hashed():
    from core.privacy.pipeline import process
    result = process("Had coffee with Alice Johnson today", source="screen_capture")
    assert "Alice Johnson" not in result["text"]
    assert "[PERSON:" in result["text"]


def test_same_name_produces_same_hash(tmp_path):
    from core.privacy.hasher import hash_name, _load_salt
    # Ensure salt file exists
    (tmp_path / "hashes").mkdir(parents=True, exist_ok=True)
    import secrets
    salt_path = tmp_path / "hashes" / "salt"
    salt = secrets.token_hex(32)
    salt_path.write_text(salt)
    salt_path.chmod(0o600)
    h1 = hash_name("Alice", salt)
    h2 = hash_name("Alice", salt)
    assert h1 == h2


def test_hash_is_eight_chars(tmp_path):
    from core.privacy.hasher import hash_name
    import secrets
    salt = secrets.token_hex(32)
    h = hash_name("Bob Smith", salt)
    assert len(h) == 8


def test_hash_display_round_trip(tmp_path):
    from core.privacy.hasher import get_or_create_hash, resolve_hash
    (tmp_path / "hashes").mkdir(parents=True, exist_ok=True)
    import secrets
    salt_path = tmp_path / "hashes" / "salt"
    salt_path.write_text(secrets.token_hex(32))
    salt_path.chmod(0o600)
    h = get_or_create_hash("Ramya Iyer")
    display = resolve_hash(h)
    assert display == "Ramya Iyer"


def test_alias_merging_same_person(tmp_path):
    from core.privacy.hasher import get_or_create_hash
    (tmp_path / "hashes").mkdir(parents=True, exist_ok=True)
    import secrets
    salt_path = tmp_path / "hashes" / "salt"
    salt_path.write_text(secrets.token_hex(32))
    salt_path.chmod(0o600)
    h1 = get_or_create_hash("Ramya")
    h2 = get_or_create_hash("Ramya")  # Same exact name
    assert h1 == h2


# --- Email and phone redaction ---

def test_email_is_redacted():
    from core.privacy.pipeline import process
    result = process("Contact me at test@example.com for details", source="gmail")
    assert "test@example.com" not in result["text"]
    assert "[EMAIL:" in result["text"]


def test_phone_is_redacted():
    from core.privacy.pipeline import process
    result = process("Call me at 555-867-5309 anytime", source="screen_capture")
    assert "555-867-5309" not in result["text"]
    assert "[PHONE:REDACTED]" in result["text"]


# --- Sensitivity scoring ---

def test_sensitivity_score_is_float_in_range():
    from core.privacy.pipeline import process
    result = process("Had lunch with Alice today", source="screen_capture")
    score = result["sensitivity_score"]
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_gmail_source_increases_score():
    from core.privacy.pipeline import process
    r_screen = process("memo note", source="screen_capture")
    r_gmail = process("memo note", source="gmail")
    assert r_gmail["sensitivity_score"] > r_screen["sensitivity_score"]


def test_pii_entities_increase_score():
    from core.privacy.pipeline import process
    r_plain = process("I went to the store today", source="screen_capture")
    r_pii = process("Alice Smith called Bob Jones about their bank account", source="screen_capture")
    assert r_pii["sensitivity_score"] > r_plain["sensitivity_score"]


def test_sensitivity_capped_at_one():
    from core.privacy.pipeline import process
    # Pile on every signal
    result = process(
        "Alice Smith emailed Bob Jones at bob@bank.com about password health doctor bank insurance",
        source="gmail",
        url="https://chase.com",
    )
    # Paused due to URL — but if not paused, score must be <= 1.0
    # Since chase.com triggers pause, check a high-signal non-paused case instead
    result2 = process(
        "Alice emailed bob@secret.org about password health doctor banking",
        source="gmail",
    )
    assert result2["sensitivity_score"] <= 1.0
