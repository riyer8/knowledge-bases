"""Tests for core/memory/relationships.py."""
from __future__ import annotations

import json

import pytest


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.privacy.hasher as hasher_mod
    import core.memory.graph as graph_mod
    import core.memory.relationships as rel_mod
    reload(hasher_mod)
    reload(graph_mod)
    reload(rel_mod)
    cfg_mod.config.ensure_dirs()
    yield tmp_path


def _setup_person(kb_root, person_hash: str, display_name: str) -> None:
    hashes_dir = kb_root / "hashes"
    hashes_dir.mkdir(parents=True, exist_ok=True)
    (hashes_dir / "salt").write_text("test-salt-hex")
    map_path = hashes_dir / "map.json"
    map_path.write_text(json.dumps({
        person_hash: {
            "display_name": display_name,
            "aliases": [],
            "first_seen": "2026-05-01T00:00:00+00:00",
        }
    }))

    graph_dir = kb_root / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "edges.json").write_text(json.dumps({
        "event-1": {
            f"person:{person_hash}": {"edge_type": "mentions", "weight": 1.0},
        },
        f"person:{person_hash}": {
            "concept:test": {"edge_type": "mentioned", "weight": 1.0},
        },
    }))


def test_list_profiles_returns_display_name(isolated_kb):
    person_hash = "abc123hash"
    _setup_person(isolated_kb, person_hash, "Alice")

    from core.memory.relationships import list_profiles

    profiles = list_profiles()
    assert len(profiles) == 1
    assert profiles[0]["display_name"] == "Alice"
    assert profiles[0]["person_hash"] == person_hash


def test_update_profile_notes(isolated_kb):
    person_hash = "abc123hash"
    _setup_person(isolated_kb, person_hash, "Alice")

    from core.memory.relationships import get_profile, update_profile

    updated = update_profile(person_hash, notes="Met at conference")
    assert updated["notes"] == "Met at conference"
    assert updated["user_edited"] is True

    profile = get_profile(person_hash)
    assert profile is not None
    assert profile["notes"] == "Met at conference"
    assert profile["connections"]


def test_update_display_name(isolated_kb):
    person_hash = "abc123hash"
    _setup_person(isolated_kb, person_hash, "Alice")

    from core.memory.relationships import update_profile

    updated = update_profile(person_hash, display_name="Alice Smith")
    assert updated["display_name"] == "Alice Smith"
