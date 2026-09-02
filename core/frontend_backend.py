#!/usr/bin/env python3
"""HTTP backend consumed by the Swift desktop app."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.config import config
from core.env_settings import get_client_settings, update_client_settings
from core.http.backend_helpers import (
    build_graph_response,
    delete_all_data,
    demo_hint,
    ingest_manual,
    load_manual_entries,
    manual_entry_meta,
    now_iso,
)
from core.http.buckets_routes import BucketsRoutesMixin
from core.http.handler_mixin import HandlerMixin
from core.http.library_routes import LibraryRoutesMixin
from core.http.relationships_routes import RelationshipsRoutesMixin
from core.http.wiki_routes import WikiRoutesMixin
from core.ingestion.pipeline import ingest_screenshot, ingest_text
from core.integrations import (
    gcal_auth_url,
    gcal_callback,
    gcal_sync,
    gmail_auth_url,
    gmail_callback,
    gmail_sync,
)
from core.llm_providers import resolve_llm_provider
from core.memory.concept_graph import list_concepts, related_for_page
from core.memory.graph import add_edge
from core.page_context_service import (
    get_connections,
    get_page,
    list_history,
    remember_passage,
    save_page_context,
    search_pages,
)
from core.retrieval.chat import answer as chat_answer
from core.retrieval.page_chat import ask_about_page
from core.library_service import get_saved_page

_SCREENSHOT_TEMP = config.events_raw_dir / "screenshots"


class FrontendHandler(
    LibraryRoutesMixin,
    BucketsRoutesMixin,
    RelationshipsRoutesMixin,
    WikiRoutesMixin,
    HandlerMixin,
    BaseHTTPRequestHandler,
):
    server_version = "KBBackend/2.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self._send_cors_headers()
        self.end_headers()

    def do_PATCH(self) -> None:
        try:
            payload = self._read_json()
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        path = urlparse(self.path).path
        if self.handle_library_patch(path, payload):
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/health":
            self._send_json(HTTPStatus.OK, {
                "ok": True,
                "service": "kb-backend",
                "api_version": 2,
                "llm_provider": resolve_llm_provider(),
                "openai_configured": bool(config.openai_api_key),
                "time": now_iso(),
                "kb_root": str(config.kb_root),
            })

        elif path == "/manual-inputs":
            self._send_json(HTTPStatus.OK, load_manual_entries())

        elif path == "/graph":
            only_orphans = query.get("orphans", ["0"])[0] == "1"
            only_unlinked = query.get("unlinked", ["0"])[0] == "1"
            folder = query.get("folder", [""])[0].strip() or None
            self._send_json(
                HTTPStatus.OK,
                build_graph_response(only_orphans, only_unlinked, folder),
            )

        elif path == "/buckets" or path.startswith("/buckets/"):
            self._handle_buckets_get(path, query)

        elif path == "/dashboard/time":
            from core.memory.buckets_service import get_summary
            days = int(query.get("days", ["7"])[0])
            self._send_json(HTTPStatus.OK, get_summary(days=days))

        elif path == "/relationships" or path.startswith("/relationships/"):
            self._handle_relationships_get(path)

        elif path == "/integrations/imessage/status":
            from core.integrations.imessage import is_available
            self._send_json(HTTPStatus.OK, {"available": is_available()})

        elif path == "/settings":
            self._send_json(HTTPStatus.OK, get_client_settings())

        elif path == "/proactive":
            try:
                from core.proactive.engine import get_insights
                insights = get_insights()
                self._send_json(HTTPStatus.OK, {"insights": insights})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/integrations/status":
            from core.integrations.oauth import load_token
            self._send_json(HTTPStatus.OK, {
                "gcal": load_token("gcal") is not None,
                "gmail": load_token("gmail") is not None,
            })

        elif path == "/integrations/gcal/auth":
            try:
                self._send_json(HTTPStatus.OK, {"url": gcal_auth_url()})
            except RuntimeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        elif path == "/integrations/gmail/auth":
            try:
                self._send_json(HTTPStatus.OK, {"url": gmail_auth_url()})
            except RuntimeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        elif path == "/integrations/gcal/callback":
            code = parse_qs(parsed.query).get("code", [""])[0]
            try:
                gcal_callback(code)
                self._send_json(HTTPStatus.OK, {"ok": True, "message": "Google Calendar connected."})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/integrations/gmail/callback":
            code = parse_qs(parsed.query).get("code", [""])[0]
            try:
                gmail_callback(code)
                self._send_json(HTTPStatus.OK, {"ok": True, "message": "Gmail connected."})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/integrations/pending":
            try:
                from core.integrations.gmail import get_pending_threads
                pending = get_pending_threads()
                self._send_json(HTTPStatus.OK, {"pending": pending})
            except RuntimeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/history":
            limit = int(query.get("limit", ["20"])[0])
            self._send_json(HTTPStatus.OK, {"history": list_history(limit=limit)})

        elif path == "/search":
            q = query.get("q", [""])[0].strip()
            top_k = int(query.get("top_k", ["8"])[0])
            if not q:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "q is required"})
                return
            self._send_json(HTTPStatus.OK, {"results": search_pages(q, top_k=top_k)})

        elif path == "/connections":
            url = query.get("url", [""])[0].strip()
            q = query.get("q", [""])[0].strip()
            top_k = int(query.get("top_k", ["5"])[0])
            self._send_json(HTTPStatus.OK, {
                "connections": get_connections(url=url, query=q, top_k=top_k),
            })

        elif path == "/concepts":
            q = query.get("q", [""])[0].strip()
            limit = int(query.get("limit", ["50"])[0])
            url = query.get("url", [""])[0].strip()
            if url or q:
                concepts = related_for_page(page_url=url, query=q, limit=limit)
            else:
                concepts = list_concepts(limit=limit)
            self._send_json(HTTPStatus.OK, {"concepts": concepts})

        elif path.startswith("/library/"):
            self._handle_library_get(path, query)

        elif self._handle_wiki_get(path, query):
            pass

        elif self._serve_web_app(path):
            pass

        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        path = urlparse(self.path).path

        if path == "/chat":
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "prompt is required"})
                return
            history = payload.get("history") or []
            include_calendar = bool(payload.get("include_calendar", True))
            try:
                reply = chat_answer(
                    prompt,
                    extra_context=demo_hint(prompt),
                    history=history,
                    include_calendar=include_calendar,
                )
                self._send_json(HTTPStatus.OK, {"reply": reply})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/buckets/override":
            event_id = str(payload.get("event_id", "")).strip()
            bucket = str(payload.get("bucket", "")).strip()
            if not event_id or not bucket:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "event_id and bucket are required"})
                return
            try:
                from core.memory.buckets_service import override_event_bucket
                result = override_event_bucket(event_id, bucket)
                self._send_json(HTTPStatus.OK, {"ok": True, **result})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        elif path.startswith("/relationships/"):
            person_hash = path.split("/relationships/", 1)[1].strip("/")
            if not person_hash:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "person hash required"})
                return
            try:
                from core.memory.relationships import update_profile
                profile = update_profile(
                    person_hash,
                    display_name=payload.get("display_name"),
                    notes=payload.get("notes"),
                )
                self._send_json(HTTPStatus.OK, {"ok": True, "profile": profile})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        elif path == "/integrations/imessage/sync":
            try:
                from core.integrations.imessage import ingest_recent
                limit = int(payload.get("limit", 20))
                self._send_json(HTTPStatus.OK, ingest_recent(limit=limit))
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/manual-input":
            kind = str(payload.get("kind", "")).strip().lower()
            value = str(payload.get("value", "")).strip()
            created_at = str(payload.get("createdAt", "")).strip() or now_iso()

            if kind not in {"text", "url", "file"} or not value:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "kind and value are required"})
                return

            try:
                event_id, timestamp = ingest_manual(kind, value, created_at)
                meta = manual_entry_meta(kind, value)
                self._send_json(HTTPStatus.OK, {"ok": True, "entry": {
                    "id": event_id,
                    "kind": kind,
                    "value": value,
                    "createdAt": timestamp,
                    "sourcePath": meta.get("source_path"),
                    "text": meta.get("text"),
                    "url": meta.get("url"),
                }})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/screenshot":
            try:
                _SCREENSHOT_TEMP.mkdir(parents=True, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                image_path = _SCREENSHOT_TEMP / f"screenshot-{ts}.png"

                result = subprocess.run(
                    ["/usr/sbin/screencapture", "-x", str(image_path)],
                    capture_output=True, timeout=10,
                )
                if result.returncode != 0:
                    raise RuntimeError("screencapture failed")

                window_title = str(payload.get("windowTitle", "") or "")
                app_name = str(payload.get("appName", "") or "")
                url = str(payload.get("url", "") or "") or None
                flagged = bool(payload.get("flaggedImportant", False))

                ingest_screenshot(
                    image_path=image_path,
                    window_title=window_title or None,
                    app_name=app_name or None,
                    url=url,
                    flagged_important=flagged,
                )
                self._send_json(HTTPStatus.OK, {
                    "ok": True,
                    "screenshot": {"filename": image_path.name},
                })
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/graph/dependency":
            source = str(payload.get("source", "")).strip()
            target = str(payload.get("target", "")).strip()
            if not source or not target or source == target:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "source and target required"})
                return
            add_edge(source, target, edge_type="manual", weight=1.0)
            self._send_json(HTTPStatus.OK, {"ok": True, "dependency": {"source": source, "target": target}})

        elif path == "/ingest":
            text = str(payload.get("text", "")).strip()
            source = str(payload.get("source", "manual_text")).strip()
            if not text:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "text is required"})
                return
            try:
                result = ingest_text(text=text, source=source)
                self._send_json(HTTPStatus.OK, {"ok": True, "event_id": result.get("id")})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/integrations/gcal/sync":
            try:
                days_back = int(payload.get("days_back", 7))
                days_forward = int(payload.get("days_forward", 14))
                count = gcal_sync(days_back=days_back, days_forward=days_forward)
                self._send_json(HTTPStatus.OK, {"ok": True, "ingested": count})
            except RuntimeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/integrations/gmail/sync":
            try:
                days_back = int(payload.get("days_back", 7))
                count = gmail_sync(days_back=days_back)
                self._send_json(HTTPStatus.OK, {"ok": True, "ingested": count})
            except RuntimeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/settings":
            try:
                settings = update_client_settings(payload)
                self._send_json(HTTPStatus.OK, {"ok": True, "settings": settings})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/delete-all":
            try:
                delete_all_data()
                self._send_json(HTTPStatus.OK, {"ok": True, "scope": "all"})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/page-context":
            try:
                record = save_page_context(payload)
                self._send_json(HTTPStatus.OK, {"ok": True, "page": record})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/ask":
            question = str(payload.get("question", "")).strip()
            saved_page_id = str(payload.get("saved_page_id", "")).strip()
            page_payload = payload.get("page")
            history = payload.get("history") or []
            stream = bool(payload.get("stream", False))

            if not question:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "question is required"})
                return

            page = None
            if saved_page_id:
                page = get_saved_page(saved_page_id)
            elif isinstance(page_payload, dict):
                page = page_payload
            if not page:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "page or saved_page_id is required"})
                return

            try:
                if stream:
                    self._stream_ask(question, page, history, saved_page_id)
                else:
                    reply = ask_about_page(
                        question,
                        page,
                        history=history,
                        stream=False,
                        saved_page_id=saved_page_id,
                    )
                    self._send_json(HTTPStatus.OK, {"reply": reply})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path.startswith("/library/"):
            self._handle_library_post(path, payload)

        elif self._handle_wiki_post(path, payload):
            pass

        elif path == "/remember":
            page_id = str(payload.get("page_id", "")).strip()
            selected_text = str(payload.get("selected_text", "")).strip()
            note = str(payload.get("note", "")).strip()
            if not page_id or not selected_text:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "page_id and selected_text are required"})
                return
            try:
                result = remember_passage(page_id, selected_text, note=note)
                self._send_json(HTTPStatus.OK, result)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if self.handle_library_delete(path):
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    config.ensure_dirs()
    port = config.backend_port
    server = HTTPServer(("127.0.0.1", port), FrontendHandler)
    print(f"KB backend listening on http://127.0.0.1:{port}")
    print(f"Storage: {config.kb_root}")
    print("Requires: ollama serve (with qwen2.5:3b and nomic-embed-text pulled)")
    server.serve_forever()


if __name__ == "__main__":
    main()
