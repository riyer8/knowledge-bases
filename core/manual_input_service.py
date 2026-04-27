from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_manual_root() -> Path:
    return Path(__file__).resolve().parents[1] / "inputs" / "manual"


MANUAL_ROOT = Path(os.getenv("KB_MANUAL_INPUT_ROOT", default_manual_root()))
UPLOADS_ROOT = MANUAL_ROOT / "uploads"
FILES_DIR = UPLOADS_ROOT / "files"
TEXT_DIR = UPLOADS_ROOT / "text"
URL_DIR = UPLOADS_ROOT / "urls"
LOG_PATH = MANUAL_ROOT / "entries.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    URL_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    if not cleaned:
        cleaned = "entry"
    return cleaned[:max_length]


def write_markdown(dir_path: Path, title: str, body: str) -> Path:
    ensure_dirs()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = f"{timestamp}-{slugify(title)}"
    candidate = dir_path / f"{base}.md"
    counter = 1
    while candidate.exists():
        candidate = dir_path / f"{base}-{counter}.md"
        counter += 1
    candidate.write_text(body, encoding="utf-8")
    return candidate


def unique_destination(path: Path) -> Path:
    candidate = FILES_DIR / path.name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        next_candidate = FILES_DIR / f"{stem}-{counter}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        counter += 1


def append_entry(entry: dict[str, Any]) -> None:
    ensure_dirs()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")


def load_entries() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows.reverse()
    return rows


def process_manual_input(kind: str, value: str, created_at: str | None = None) -> dict[str, Any]:
    kind = kind.strip().lower()
    value = value.strip()
    created = (created_at or "").strip() or now_iso()
    if kind not in {"file", "url", "text"} or not value:
        raise ValueError("Payload must include valid kind and value")

    entry: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "receivedAt": now_iso(),
        "createdAt": created,
    }
    if kind == "file":
        source_path = Path(value)
        if not source_path.exists() or not source_path.is_file():
            raise ValueError("File path does not exist")
        ensure_dirs()
        destination = unique_destination(source_path)
        shutil.copy2(source_path, destination)
        entry["value"] = str(destination.relative_to(MANUAL_ROOT))
        entry["sourcePath"] = str(source_path)
    elif kind == "text":
        md_path = write_markdown(TEXT_DIR, title="manual-text", body=value)
        entry["value"] = str(md_path.relative_to(MANUAL_ROOT))
        entry["text"] = value
    elif kind == "url":
        md_path = write_markdown(URL_DIR, title=value, body=f"# Saved URL\n\n{value}\n")
        entry["value"] = str(md_path.relative_to(MANUAL_ROOT))
        entry["url"] = value

    append_entry(entry)
    return entry
