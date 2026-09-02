from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.config import config


def _load_salt() -> str:
    salt_path = config.hash_salt_path
    if salt_path.exists():
        return salt_path.read_text().strip()
    # First run: generate and persist salt
    salt = secrets.token_hex(32)
    salt_path.parent.mkdir(parents=True, exist_ok=True)
    salt_path.write_text(salt)
    salt_path.chmod(0o600)
    return salt


def _load_map() -> dict:
    map_path = config.hash_map_path
    if map_path.exists():
        return json.loads(map_path.read_text())
    return {}


def _save_map(hash_map: dict) -> None:
    map_path = config.hash_map_path
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(json.dumps(hash_map, indent=2))


def _normalize(name: str) -> str:
    import re  # noqa: PLC0415
    return re.sub(r"[^\w\s]", "", name.lower()).strip()


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def hash_name(name: str, salt: Optional[str] = None) -> str:
    """Return 8-char truncated SHA-256 hash for a name."""
    if salt is None:
        salt = _load_salt()
    normalized = _normalize(name)
    digest = hashlib.sha256((normalized + salt).encode()).hexdigest()
    return digest[:8]


def get_or_create_hash(name: str) -> str:
    """
    Hash the name, register it in the map (with alias merging), and return the hash.
    """
    salt = _load_salt()
    normalized = _normalize(name)
    h = hash_name(name, salt)
    hash_map = _load_map()

    # Check alias merging — if any existing normalized alias is close, reuse that entry
    for existing_hash, entry in hash_map.items():
        existing_aliases = [_normalize(a) for a in entry.get("aliases", [])]
        existing_display = _normalize(entry.get("display_name", ""))
        all_forms = [existing_display] + existing_aliases
        for form in all_forms:
            if _levenshtein(normalized, form) < 2:
                # Merge: add as alias to the existing entry
                if name not in entry.get("aliases", []):
                    entry.setdefault("aliases", []).append(name)
                    _save_map(hash_map)
                return existing_hash

    # New person
    if h not in hash_map:
        hash_map[h] = {
            "display_name": name,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "aliases": [name],
            "user_edited": False,
        }
        _save_map(hash_map)

    return h


def resolve_hash(h: str) -> Optional[str]:
    """Return the display name for a hash, or None if unknown."""
    hash_map = _load_map()
    entry = hash_map.get(h)
    return entry["display_name"] if entry else None


def update_display_name(person_hash: str, display_name: str) -> None:
    """User-edited display name for a person hash."""
    hash_map = _load_map()
    entry = hash_map.get(person_hash, {
        "display_name": display_name,
        "aliases": [],
        "first_seen": datetime.now(timezone.utc).isoformat(),
    })
    entry["display_name"] = display_name.strip()
    entry["user_edited"] = True
    entry.setdefault("aliases", [])
    hash_map[person_hash] = entry
    _save_map(hash_map)
