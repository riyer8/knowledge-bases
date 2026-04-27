#!/usr/bin/env python3
"""Manual input-only backend."""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_ROOT))
from core.manual_input_service import MANUAL_ROOT, ensure_dirs, load_entries, now_iso, process_manual_input


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

        kind = str(payload.get("kind", ""))
        value = str(payload.get("value", ""))
        created_at = str(payload.get("createdAt", "")).strip() or None
        try:
            entry = process_manual_input(kind=kind, value=value, created_at=created_at)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Failed to process input: {exc}"})
            return

        self._send_json(HTTPStatus.OK, {"ok": True, "entry": entry})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "manualRoot": str(MANUAL_ROOT),
                    "time": now_iso(),
                },
            )
            return

        if path == "/manual-inputs":
            self._send_json(HTTPStatus.OK, load_entries())
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    ensure_dirs()
    server = HTTPServer(("127.0.0.1", 8765), ManualInputHandler)
    print("Manual input-only backend listening on http://127.0.0.1:8765")
    print(f"Writing to: {MANUAL_ROOT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
