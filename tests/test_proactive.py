"""Tests for core/proactive/ insights."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.memory.bucket_classifier as bc_mod
    import core.memory.buckets_service as bs_mod
    import core.proactive.life_balance as lb_mod
    reload(bc_mod)
    reload(bs_mod)
    reload(lb_mod)
    cfg_mod.config.ensure_dirs()
    yield tmp_path


def _seed_work_heavy_week(kb_root) -> None:
    clean_dir = kb_root / "events" / "clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    log = clean_dir / "2026-05-27.jsonl"
    buckets_dir = kb_root / "buckets"
    buckets_dir.mkdir(parents=True, exist_ok=True)
    classifications = {}

    for i in range(10):
        event_id = f"work-{i}"
        event = {
            "id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "manual_text",
            "content": {"text": f"standup sprint jira task {i}"},
        }
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
        classifications[event_id] = {"bucket": "Work/Deep Work", "confidence": 1.0}

    (buckets_dir / "classifications.json").write_text(json.dumps(classifications))


def test_life_balance_detects_heavy_work_week(isolated_kb):
    _seed_work_heavy_week(isolated_kb)

    from core.proactive.life_balance import life_balance_insights

    insights = life_balance_insights(days=7)
    assert any(i["type"] == "balance" and "work" in i["title"].lower() for i in insights)


def test_get_insights_includes_balance(monkeypatch, isolated_kb):
    _seed_work_heavy_week(isolated_kb)
    monkeypatch.setattr(
        "core.proactive.engine.upcoming_events",
        lambda minutes_ahead=60: [],
    )
    monkeypatch.setattr(
        "core.proactive.engine.pending_emails",
        lambda: [],
    )
    monkeypatch.setattr(
        "core.proactive.engine.relationship_drift",
        lambda inactive_days=14: [],
    )

    from core.proactive.engine import get_insights

    insights = get_insights(max_insights=5)
    assert any(i.get("type") == "balance" for i in insights)
