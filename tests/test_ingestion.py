"""Tests for core/ingestion/."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.privacy.pipeline as pp
    import core.ingestion.pipeline as ip
    import core.ingestion.event_writer as ew
    import core.memory.store as ms
    import core.memory.vector_store as vs
    import core.memory.bucket_classifier as bc
    import core.memory.graph as g
    for mod in (pp, ew, vs, bc, g, ms, ip):
        reload(mod)
    yield tmp_path


def _fake_embed(text: str) -> list[float]:
    return [0.1] * 64


# --- ingest_text ---

def test_ingest_text_writes_clean_event(tmp_path, monkeypatch):
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", _fake_embed)

    from core.ingestion.pipeline import ingest_text
    result = ingest_text("I had a great run this morning", source="manual_text")

    assert result["raw_event"] is False
    assert result["source"] == "manual_text"

    clean_dir = tmp_path / "events" / "clean"
    files = list(clean_dir.glob("*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text().strip().split("\n")
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["source"] == "manual_text"
    assert event["raw_event"] is False


def test_ingest_text_writes_raw_event(tmp_path, monkeypatch):
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", _fake_embed)

    from core.ingestion.pipeline import ingest_text
    ingest_text("bought groceries", source="manual_text")

    raw_dir = tmp_path / "events" / "raw"
    files = list(raw_dir.glob("*.jsonl"))
    assert len(files) == 1
    event = json.loads(files[0].read_text().strip())
    assert event["raw_event"] is True


def test_ingest_text_paused_event_not_written_to_clean(tmp_path, monkeypatch):
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", _fake_embed)

    from core.ingestion.pipeline import ingest_text
    # Banking keyword in URL won't apply here since ingest_text has no URL param for pause
    # Instead mock privacy to return pause
    import core.ingestion.pipeline as ip
    import core.privacy.pipeline as pp
    original_process = pp.process

    def pausing_process(*args, **kwargs):
        result = original_process(*args, **kwargs)
        result["should_pause"] = True
        result["pause_reason"] = "test_pause"
        result["text"] = ""
        return result

    monkeypatch.setattr(ip, "privacy_process", pausing_process)

    result = ingest_text("some sensitive content", source="manual_text")
    assert result["should_pause"] is True

    clean_dir = tmp_path / "events" / "clean"
    assert not any(clean_dir.glob("*.jsonl"))


def test_ingest_text_feeds_memory(tmp_path, monkeypatch):
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", _fake_embed)

    from core.ingestion.pipeline import ingest_text
    ingest_text("attended a team standup meeting", source="manual_text")

    index_path = tmp_path / "index" / "chunks.json"
    assert index_path.exists()
    chunks = json.loads(index_path.read_text())
    assert len(chunks) > 0


def test_ingest_text_classifies_into_bucket(tmp_path, monkeypatch):
    import core.memory.vector_store as vs
    monkeypatch.setattr(vs, "embed", _fake_embed)

    from core.ingestion.pipeline import ingest_text
    ingest_text("went for a run today, 5km", source="manual_text")

    classifications_path = tmp_path / "buckets" / "classifications.json"
    assert classifications_path.exists()
    data = json.loads(classifications_path.read_text())
    assert len(data) == 1
    bucket = list(data.values())[0]["bucket"]
    assert bucket == "Health/Fitness"


# --- ingest_screenshot ---

def test_ingest_screenshot_deletes_image(tmp_path, monkeypatch):
    import core.memory.vector_store as vs
    import core.ingestion.ocr as ocr_mod
    monkeypatch.setattr(vs, "embed", _fake_embed)
    monkeypatch.setattr(ocr_mod, "extract_text", lambda path: "some captured text")

    fake_image = tmp_path / "test_screenshot.png"
    fake_image.write_bytes(b"fake image data")

    from core.ingestion.pipeline import ingest_screenshot
    ingest_screenshot(fake_image, window_title="Notes", app_name="Notes")

    assert not fake_image.exists()


def test_ingest_screenshot_writes_clean_event(tmp_path, monkeypatch):
    import core.memory.vector_store as vs
    import core.ingestion.ocr as ocr_mod
    monkeypatch.setattr(vs, "embed", _fake_embed)
    monkeypatch.setattr(ocr_mod, "extract_text", lambda path: "read a great article about AI")

    fake_image = tmp_path / "shot.png"
    fake_image.write_bytes(b"fake")

    from core.ingestion.pipeline import ingest_screenshot
    result = ingest_screenshot(fake_image)

    assert result["source"] == "screen_capture"
    clean_files = list((tmp_path / "events" / "clean").glob("*.jsonl"))
    assert len(clean_files) == 1


def test_ingest_screenshot_pauses_on_sensitive_url(tmp_path, monkeypatch):
    import core.memory.vector_store as vs
    import core.ingestion.ocr as ocr_mod
    monkeypatch.setattr(vs, "embed", _fake_embed)
    monkeypatch.setattr(ocr_mod, "extract_text", lambda path: "account balance $500")

    fake_image = tmp_path / "shot.png"
    fake_image.write_bytes(b"fake")

    from core.ingestion.pipeline import ingest_screenshot
    result = ingest_screenshot(fake_image, url="https://chase.com/accounts")

    assert result["should_pause"] is True
    # Image still deleted even on pause
    assert not fake_image.exists()
    # No clean event written
    clean_dir = tmp_path / "events" / "clean"
    assert not any(clean_dir.glob("*.jsonl"))
