from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from core.retrieval.page_chat import ask_about_page


class HandlerMixin:
    """Shared JSON/CORS helpers for route mixins."""

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b""
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _stream_ask(
        self,
        question: str,
        page: dict,
        history: list[dict[str, str]],
        saved_page_id: str = "",
    ) -> None:
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._send_cors_headers()
        self.end_headers()

        try:
            stream = ask_about_page(
                question,
                page,
                history=history,
                stream=True,
                saved_page_id=saved_page_id,
            )
            for token in stream:  # type: ignore[union-attr]
                data = json.dumps({"token": token})
                self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
            self.wfile.write(b"data: {\"done\": true}\n\n")
            self.wfile.flush()
        except Exception as exc:
            data = json.dumps({"error": str(exc)})
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            self.wfile.flush()
