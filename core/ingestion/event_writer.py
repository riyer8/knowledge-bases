from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.config import config


def write_raw(event: dict) -> Path:
    """Append a raw event to the raw event log. Returns the file path."""
    config.events_raw_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = config.events_raw_dir / f"{date_str}.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(event) + "\n")
    return path


def write_clean(event: dict) -> Path:
    """Append a clean (post-privacy) event to the clean event log. Returns the file path."""
    config.events_clean_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = config.events_clean_dir / f"{date_str}.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(event) + "\n")
    return path
