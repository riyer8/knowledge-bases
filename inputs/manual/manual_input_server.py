#!/usr/bin/env python3
"""Local backend for manual input ingestion."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


def default_manual_root() -> Path:
    return Path(__file__).resolve().parent


MANUAL_ROOT = Path(os.getenv("KB_MANUAL_INPUT_ROOT", default_manual_root()))
FILES_DIR = MANUAL_ROOT / "files"
LOG_PATH = MANUAL_ROOT / "entries.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    FILES_DIR.mkdir(parents=True, exist_ok=True)


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


class ManualInputHandler(BaseHTTPRequestHandler):
    server_version = "ManualInputServer/1.0"

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/manual-input":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload_raw = self.rfile.read(content_length)
            payload = json.loads(payload_raw.decode("utf-8"))
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"})
            return

        kind = str(payload.get("kind", "")).strip().lower()
        value = str(payload.get("value", "")).strip()
        created_at = str(payload.get("createdAt", "")).strip() or now_iso()

        if kind not in {"file", "url", "text"} or not value:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Payload must include valid kind and value"})
            return

        entry: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "kind": kind,
            "receivedAt": now_iso(),
            "createdAt": created_at,
        }

        try:
            if kind == "file":
                source_path = Path(value)
                if not source_path.exists() or not source_path.is_file():
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "File path does not exist"})
                    return

                ensure_dirs()
                destination = unique_destination(source_path)
                shutil.copy2(source_path, destination)
                entry["value"] = str(destination.relative_to(MANUAL_ROOT))
                entry["sourcePath"] = str(source_path)
            else:
                entry["value"] = value

            append_entry(entry)
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Failed to process input: {exc}"})
            return

        self._send_json(HTTPStatus.OK, {"ok": True, "entry": entry})

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "manualRoot": str(MANUAL_ROOT),
                    "time": now_iso(),
                },
            )
            return

        if self.path == "/manual-inputs":
            self._send_json(HTTPStatus.OK, load_entries())
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    ensure_dirs()
    server = HTTPServer(("127.0.0.1", 8765), ManualInputHandler)
    print("Manual input backend listening on http://127.0.0.1:8765")
    print(f"Writing to: {MANUAL_ROOT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
