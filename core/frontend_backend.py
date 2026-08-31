#!/usr/bin/env python3
"""HTTP backend consumed by the Swift desktop app."""

from __future__ import annotations

import json
import shutil
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
from core.ingestion.pipeline import ingest_screenshot, ingest_text
from core.memory.graph import load_graph, add_edge
from core.retrieval.chat import answer as chat_answer
from core.integrations import (
    gcal_sync, gcal_auth_url, gcal_callback,
    gmail_sync, gmail_auth_url, gmail_callback,
)
from core.library_service import (
    clear_library,
    delete_saved_page,
    explore_suggestions,
    find_saved_page_by_url,
    get_saved_page,
    graph_visual,
    list_quotes,
    list_saved_pages,
    save_page as library_save_page,
    save_quote,
)
from core.memory.concept_graph import list_concepts, related_for_page
from core.page_context_service import (
    get_connections,
    get_page,
    list_history,
    remember_passage,
    save_page_context,
    search_pages,
)
from core.retrieval.page_chat import ask_about_page
from core.llm_providers import resolve_llm_provider

# Temporary landing dir for raw screenshots before OCR
_SCREENSHOT_TEMP = config.events_raw_dir / "screenshots"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Graph helpers — translate adjacency dict → MarkdownGraph shape the UI needs
# ---------------------------------------------------------------------------

def _build_graph_response(
    only_orphans: bool = False,
    only_unlinked: bool = False,
    folder_filter: str | None = None,
) -> dict:
    adjacency = load_graph()

    # Collect all node IDs
    all_node_ids: set[str] = set(adjacency.keys())
    for neighbors in adjacency.values():
        all_node_ids.update(neighbors.keys())

    # Count degrees
    incoming: dict[str, int] = {n: 0 for n in all_node_ids}
    outgoing: dict[str, int] = {n: 0 for n in all_node_ids}
    edges: list[dict] = []
    manual_deps: list[dict] = []

    for source, neighbors in adjacency.items():
        for target, meta in neighbors.items():
            edge_type = meta.get("edge_type", "")
            outgoing[source] = outgoing.get(source, 0) + 1
            incoming[target] = incoming.get(target, 0) + 1
            entry = {"source": source, "target": target}
            if edge_type == "manual":
                manual_deps.append(entry)
            else:
                edges.append(entry)

    def _folder(node_id: str) -> str:
        if node_id.startswith("person:"):
            return "people"
        if node_id.startswith("bucket:"):
            return "buckets"
        return "events"

    def _label(node_id: str) -> str:
        if node_id.startswith("person:"):
            return node_id[7:][:16]
        if node_id.startswith("bucket:"):
            return node_id[7:][:16]
        return node_id[:16]

    nodes = []
    folders: set[str] = set()
    for node_id in all_node_ids:
        folder = _folder(node_id)
        if folder_filter and folder != folder_filter:
            continue
        ic = incoming.get(node_id, 0)
        oc = outgoing.get(node_id, 0)
        is_orphan = ic == 0 and oc == 0
        is_unlinked = oc == 0
        if only_orphans and not is_orphan:
            continue
        if only_unlinked and not is_unlinked:
            continue
        nodes.append({
            "id": node_id,
            "label": _label(node_id),
            "path": node_id,
            "folder": folder,
            "incoming": ic,
            "outgoing": oc,
            "degree": ic + oc,
            "isOrphan": is_orphan,
            "isUnlinked": is_unlinked,
        })
        folders.add(folder)

    return {
        "nodes": nodes,
        "edges": edges,
        "manualDependencies": manual_deps,
        "folders": sorted(folders),
    }


# ---------------------------------------------------------------------------
# Manual inputs — read from clean event log, return BackendEntry shapes
# ---------------------------------------------------------------------------

def _load_manual_entries() -> list[dict]:
    manual_sources = {"manual_text", "manual_url", "manual_file"}
    entries: list[dict] = []
    clean_dir = config.events_clean_dir
    if not clean_dir.exists():
        return entries

    for log_file in sorted(clean_dir.glob("*.jsonl"), reverse=True):
        for line in log_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("source") not in manual_sources:
                continue
            meta = event.get("content", {}).get("metadata", {})
            entries.append({
                "id": event.get("id", ""),
                "kind": meta.get("kind", event.get("source", "text").replace("manual_", "")),
                "value": meta.get("value", ""),
                "createdAt": event.get("timestamp", ""),
                "sourcePath": meta.get("source_path"),
                "text": meta.get("text"),
                "url": meta.get("url"),
            })

    return entries


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class FrontendHandler(BaseHTTPRequestHandler):
    server_version = "KBBackend/2.0"

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
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

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self._send_cors_headers()
        self.end_headers()

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
                "time": _now_iso(),
                "kb_root": str(config.kb_root),
            })

        elif path == "/manual-inputs":
            self._send_json(HTTPStatus.OK, _load_manual_entries())

        elif path == "/graph":
            only_orphans = query.get("orphans", ["0"])[0] == "1"
            only_unlinked = query.get("unlinked", ["0"])[0] == "1"
            folder = query.get("folder", [""])[0].strip() or None
            self._send_json(HTTPStatus.OK, _build_graph_response(only_orphans, only_unlinked, folder))

        elif path == "/buckets":
            from core.memory.bucket_classifier import _load_classifications
            self._send_json(HTTPStatus.OK, _load_classifications())

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
            try:
                reply = chat_answer(prompt, extra_context=_demo_hint(prompt))
                self._send_json(HTTPStatus.OK, {"reply": reply})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        elif path == "/manual-input":
            kind = str(payload.get("kind", "")).strip().lower()
            value = str(payload.get("value", "")).strip()
            created_at = str(payload.get("createdAt", "")).strip() or _now_iso()

            if kind not in {"text", "url", "file"} or not value:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "kind and value are required"})
                return

            try:
                event_id, timestamp = _ingest_manual(kind, value, created_at)
                meta = _manual_entry_meta(kind, value)
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

        elif path == "/delete-all":
            try:
                _delete_all()
                self._send_json(HTTPStatus.OK, {"ok": True})
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
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/library/pages/"):
            page_id = path.split("/library/pages/", 1)[1].strip("/")
            if not page_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "page id required"})
                return
            deleted = delete_saved_page(page_id)
            if not deleted:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "page not found"})
                return
            self._send_json(HTTPStatus.OK, {"ok": True})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def _handle_library_get(self, path: str, query: dict) -> None:
        if path == "/library/pages":
            limit = int(query.get("limit", ["100"])[0])
            self._send_json(HTTPStatus.OK, {"pages": list_saved_pages(limit=limit)})
            return
        if path == "/library/graph":
            self._send_json(HTTPStatus.OK, graph_visual())
            return
        if path == "/library/quotes":
            page_id = query.get("page_id", [""])[0].strip()
            page_url = query.get("page_url", [""])[0].strip()
            self._send_json(HTTPStatus.OK, {
                "quotes": list_quotes(page_id=page_id, page_url=page_url),
            })
            return
        if path.startswith("/library/pages/"):
            page_id = path.split("/library/pages/", 1)[1].strip("/")
            page = get_saved_page(page_id)
            if not page:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "page not found"})
                return
            self._send_json(HTTPStatus.OK, {"page": page})
            return
        if path == "/library/by-url":
            url = query.get("url", [""])[0].strip()
            page = find_saved_page_by_url(url) if url else None
            self._send_json(HTTPStatus.OK, {"page": page})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def _handle_library_post(self, path: str, payload: dict) -> None:
        try:
            if path == "/library/save-page":
                page_data = payload.get("page")
                if not isinstance(page_data, dict):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "page is required"})
                    return
                history = payload.get("history") or []
                record = library_save_page(page_data, chat_history=history)
                self._send_json(HTTPStatus.OK, {"ok": True, "page": record})
                return
            if path == "/library/quotes":
                text = str(payload.get("text", "")).strip()
                if not text:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "text is required"})
                    return
                quote = save_quote(
                    text=text,
                    page_id=str(payload.get("page_id", "")).strip(),
                    page_url=str(payload.get("page_url", "")).strip(),
                    page_title=str(payload.get("page_title", "")).strip(),
                    note=str(payload.get("note", "")).strip(),
                )
                self._send_json(HTTPStatus.OK, {"ok": True, "quote": quote})
                return
            if path == "/library/explore":
                page = payload.get("page")
                if not isinstance(page, dict):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "page is required"})
                    return
                suggestions = explore_suggestions(page)
                self._send_json(HTTPStatus.OK, {"suggestions": suggestions})
                return
            if path == "/library/clear":
                _delete_all()
                self._send_json(HTTPStatus.OK, {"ok": True})
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return  # silence default access log

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manual_entry_meta(kind: str, value: str) -> dict:
    if kind == "text":
        return {"kind": "text", "value": value, "text": value}
    if kind == "url":
        return {"kind": "url", "value": value, "url": value}
    # file
    return {"kind": "file", "value": value, "source_path": value}


def _ingest_manual(kind: str, value: str, created_at: str) -> tuple[str, str]:
    """Run manual input through the ingestion pipeline. Returns (event_id, timestamp)."""
    meta = _manual_entry_meta(kind, value)

    if kind == "file":
        source_path = Path(value)
        if not source_path.exists() or not source_path.is_file():
            raise ValueError(f"File not found: {value}")
        text = source_path.read_text(encoding="utf-8", errors="ignore")
        meta["source_path"] = str(source_path)
    elif kind == "url":
        text = value  # URL stored as text; full fetch handled by future web-scraper module
    else:
        text = value

    result = ingest_text(text=text, source=f"manual_{kind}", metadata=meta)
    return result.get("id", ""), result.get("processed_at", created_at)


_SYMSYS_HINT = (
    "The user is asking about their Symsys161 project. "
    "You have notes about this Stanford course in your knowledge base — it is the Symbolic Systems 161 "
    "speaker series class about technology and human augmentation. "
    "Start your response by warmly asking 'Is this Symsys161 from Canvas — the speaker series class?' "
    "to confirm you have the right context. Then give specific, actionable presentation advice. "
    "Key points to weave in naturally: (1) the harness must be crystal clear — the rubric asks "
    "whether the audience understands what they are watching at every step; "
    "(2) lead with the problem before showing the tool; "
    "(3) show the full capture-to-retrieval loop live with the butterfly; "
    "(4) connect to the course augmentation theme; "
    "(5) seed demo data before presenting so chat is fast. "
    "Be warm and conversational, not a bullet-point list."
)

_PRESENTATION_FOLLOWUP_HINT = (
    "The user is continuing a conversation about their Symsys161 class presentation. "
    "Give them practical, specific follow-up advice. Cover: warming up Ollama before presenting, "
    "having a fallback plan if the live demo lags, Q&A prep (why local? why not Notion? why not Rewind?), "
    "and a suggested 10-minute slide structure. Keep it encouraging and conversational."
)


def _demo_hint(prompt: str) -> str | None:
    """Return an extra_context hint to steer the LLM, or None to use default RAG."""
    lower = prompt.lower()
    is_symsys = "symsys" in lower or (
        "161" in lower
        and any(k in lower for k in ("class", "project", "presentation", "course", "canvas", "sift", "help"))
    )
    if is_symsys:
        return _SYMSYS_HINT
    is_followup = (
        any(k in lower for k in ("yes", "yeah", "yep", "more", "worried", "nervous", "help", "how"))
        and any(k in lower for k in ("presentation", "present", "demo", "talk", "slide", "class"))
    )
    if is_followup:
        return _PRESENTATION_FOLLOWUP_HINT
    return None


def _delete_all() -> None:
    """Wipe all runtime data under ~/.kb/."""
    clear_library()
    for subdir in [
        config.events_raw_dir,
        config.events_clean_dir,
        config.index_dir,
        config.graph_dir,
        config.hashes_dir,
        config.buckets_dir,
        config.pages_dir,
    ]:
        if subdir.exists():
            shutil.rmtree(subdir)
    config.ensure_dirs()


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
