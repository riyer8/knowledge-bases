#!/usr/bin/env python3
"""Chrome native messaging host — starts the Context Python backend."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
START_SCRIPT = REPO_ROOT / "scripts" / "start_backend.sh"


def read_message() -> dict | None:
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    length = struct.unpack("<I", raw_length)[0]
    if length <= 0:
        return None
    data = sys.stdin.buffer.read(length)
    return json.loads(data.decode("utf-8"))


def send_message(message: dict) -> None:
    encoded = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def handle(message: dict) -> dict:
    action = message.get("action", "start")
    if action not in {"start", "ping"}:
        return {"ok": False, "error": f"Unknown action: {action}"}

    if not START_SCRIPT.exists():
        return {"ok": False, "error": f"Missing start script: {START_SCRIPT}"}

    result = subprocess.run(
        ["bash", str(START_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    status = (result.stdout or "").strip() or "unknown"
    ok = status in {"started", "already_running"}
    payload: dict = {"ok": ok, "status": status}
    if not ok:
        stderr = (result.stderr or "").strip()
        payload["error"] = stderr or "Backend failed to start"
    return payload


def main() -> None:
    while True:
        message = read_message()
        if message is None:
            break
        send_message(handle(message))


if __name__ == "__main__":
    main()
