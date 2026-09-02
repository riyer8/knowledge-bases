"""Relationship profiles built from the person graph and hash map."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from core.config import config
from core.memory.graph import get_neighbors, get_person_events, load_graph
from core.privacy.hasher import _load_map, resolve_hash, update_display_name


def _profiles_path():
    return config.kb_root / "relationships" / "profiles.json"


def _load_profiles() -> dict[str, Any]:
    path = _profiles_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_profiles(data: dict[str, Any]) -> None:
    path = _profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _person_hashes() -> list[str]:
    graph = load_graph()
    hashes: set[str] = set()
    for node in graph:
        if node.startswith("person:"):
            hashes.add(node[len("person:"):])
    hash_map = _load_map()
    hashes.update(hash_map.keys())
    return sorted(hashes)


def list_profiles(limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 500))
    profiles = _load_profiles()
    hash_map = _load_map()
    results: list[dict[str, Any]] = []

    for person_hash in _person_hashes()[:limit]:
        entry = hash_map.get(person_hash, {})
        profile = profiles.get(person_hash, {})
        event_count = len(get_person_events(person_hash))
        results.append({
            "person_hash": person_hash,
            "display_name": resolve_hash(person_hash) or person_hash,
            "aliases": entry.get("aliases", []),
            "first_seen": entry.get("first_seen"),
            "event_count": event_count,
            "notes": profile.get("notes", ""),
            "user_edited": bool(entry.get("user_edited") or profile.get("user_edited")),
            "last_updated": profile.get("updated_at"),
        })

    results.sort(key=lambda p: (-p["event_count"], p["display_name"]))
    return results


def get_profile(person_hash: str) -> dict[str, Any] | None:
    matches = [p for p in list_profiles(limit=500) if p["person_hash"] == person_hash]
    if not matches:
        return None

    profile = matches[0]
    neighbors = get_neighbors(f"person:{person_hash}")
    profile["connections"] = [
        {"node": n["node"], "edge_type": n.get("edge_type"), "weight": n.get("weight")}
        for n in neighbors[:20]
    ]
    return profile


def update_profile(
    person_hash: str,
    *,
    display_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    hash_map = _load_map()
    if person_hash not in hash_map and display_name is None:
        raise ValueError("unknown person hash")

    if display_name is not None:
        update_display_name(person_hash, display_name)

    profiles = _load_profiles()
    record = profiles.get(person_hash, {})
    if notes is not None:
        record["notes"] = notes.strip()
        record["user_edited"] = True
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    profiles[person_hash] = record
    _save_profiles(profiles)

    result = get_profile(person_hash)
    if result is None:
        raise ValueError("profile not found after update")
    return result
