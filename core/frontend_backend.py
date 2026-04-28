#!/usr/bin/env python3
"""Unified backend used by the Swift UI."""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
if str(REPO_ROOT / "inputs") not in sys.path:
    sys.path.append(str(REPO_ROOT / "inputs"))

from core.data_reset_service import delete_all_runtime_data
from core.graph_service import add_manual_dependency, build_markdown_graph
from core.llm_service import call_claude_chat
from core.manual_input_service import MANUAL_ROOT, load_entries, now_iso, process_manual_input
from screenshot.screenshot_service import capture_screenshot

GRAPH_ROOT = Path((REPO_ROOT))
SCREENSHOT_ROOT = REPO_ROOT / "inputs" / "screenshot" / "captures"


class FrontendHandler(BaseHTTPRequestHandler):
    server_version = "FrontendBackend/1.0"

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path not in {"/manual-input", "/chat", "/screenshot", "/graph/dependency", "/delete-all"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        payload: dict[str, Any] = {}
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload_raw = self.rfile.read(content_length) if content_length > 0 else b""
            if payload_raw:
                payload = json.loads(payload_raw.decode("utf-8"))
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"})
            return

        if self.path == "/graph/dependency":
            source = str(payload.get("source", "")).strip()
            target = str(payload.get("target", "")).strip()
            try:
                dependency = add_manual_dependency(GRAPH_ROOT, source, target)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Failed to save dependency: {exc}"})
                return
            self._send_json(HTTPStatus.OK, {"ok": True, "dependency": dependency})
            return

        if self.path == "/manual-input":
            kind = str(payload.get("kind", ""))
            value = str(payload.get("value", ""))
            created_at = str(payload.get("createdAt", "")).strip() or None
            try:
                entry = process_manual_input(kind=kind, value=value, created_at=created_at)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Failed to process input: {exc}"}
                )
                return
            self._send_json(HTTPStatus.OK, {"ok": True, "entry": entry})
            return

        if self.path == "/chat":
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Payload must include prompt"})
                return
            self._send_json(HTTPStatus.OK, {"reply": call_claude_chat(prompt, load_entries())})
            return

        if self.path == "/delete-all":
            try:
                delete_all_runtime_data(
                    manual_root=MANUAL_ROOT,
                    graph_root=GRAPH_ROOT,
                    screenshot_root=SCREENSHOT_ROOT,
                )
                self._send_json(HTTPStatus.OK, {"ok": True})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Failed to delete data: {exc}"})
            return

        try:
            shot = capture_screenshot(SCREENSHOT_ROOT)
            self._send_json(HTTPStatus.OK, {"ok": True, "screenshot": shot})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Screenshot failed: {exc}"})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "manualRoot": str(MANUAL_ROOT),
                    "time": now_iso(),
                    "service": "frontend-backend",
                },
            )
            return

        if path == "/manual-inputs":
            self._send_json(HTTPStatus.OK, load_entries())
            return

        if path == "/graph":
            only_orphans = query.get("orphans", ["0"])[0] == "1"
            only_unlinked = query.get("unlinked", ["0"])[0] == "1"
            folder = query.get("folder", [""])[0].strip() or None
            self._send_json(
                HTTPStatus.OK,
                build_markdown_graph(
                    GRAPH_ROOT,
                    only_orphans=only_orphans,
                    only_unlinked=only_unlinked,
                    folder_prefix=folder,
                ),
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = HTTPServer(("127.0.0.1", 8765), FrontendHandler)
    print("Frontend backend listening on http://127.0.0.1:8765")
    print(f"Manual store: {MANUAL_ROOT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
