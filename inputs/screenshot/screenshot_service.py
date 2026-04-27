#!/usr/bin/env python3
"""Screenshot capture helpers for backend hotkeys."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def capture_screenshot(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
    target = output_dir / filename

    cmd = ["/usr/sbin/screencapture", "-x", str(target)]
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or "screencapture failed")

    return {
        "path": str(target),
        "filename": filename,
    }
