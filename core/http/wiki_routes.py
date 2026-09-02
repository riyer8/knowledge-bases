from __future__ import annotations

import mimetypes
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote, urlparse

from core.library_service import get_saved_page
from core.wiki_service import (
    compile_wiki,
    get_article,
    get_raw,
    health_check,
    ingest_from_saved_page,
    ingest_raw,
    list_articles,
    list_raw,
    read_index,
    search_wiki,
    wiki_status,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WEB_ROOT = _REPO_ROOT / "web"


class WikiRoutesMixin:
    def _handle_wiki_get(self, path: str, query: dict) -> bool:
        if path == "/wiki/status":
            self._send_json(HTTPStatus.OK, wiki_status())
            return True
        if path == "/wiki/index":
            self._send_json(HTTPStatus.OK, {"index": read_index()})
            return True
        if path == "/wiki/raw":
            limit = int(query.get("limit", ["100"])[0])
            self._send_json(HTTPStatus.OK, {"raw": list_raw(limit=limit)})
            return True
        if path.startswith("/wiki/raw/"):
            raw_id = path.split("/wiki/raw/", 1)[1].strip("/")
            raw = get_raw(raw_id)
            if not raw:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "raw source not found"})
                return True
            self._send_json(HTTPStatus.OK, {"raw": raw})
            return True
        if path == "/wiki/articles":
            limit = int(query.get("limit", ["200"])[0])
            self._send_json(HTTPStatus.OK, {"articles": list_articles(limit=limit)})
            return True
        if path.startswith("/wiki/articles/"):
            slug = path.split("/wiki/articles/", 1)[1].strip("/")
            article = get_article(slug)
            if not article:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "article not found"})
                return True
            self._send_json(HTTPStatus.OK, {"article": article})
            return True
        if path == "/wiki/search":
            q = query.get("q", [""])[0].strip()
            limit = int(query.get("limit", ["20"])[0])
            self._send_json(HTTPStatus.OK, {"results": search_wiki(q, limit=limit)})
            return True
        return False

    def _handle_wiki_post(self, path: str, payload: dict) -> bool:
        if path == "/wiki/ingest":
            page_id = str(payload.get("page_id", "")).strip()
            if page_id:
                page = get_saved_page(page_id)
                if not page:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "saved page not found"})
                    return True
                try:
                    record = ingest_from_saved_page(page)
                    self._send_json(HTTPStatus.OK, {"ok": True, "raw": record})
                except ValueError as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return True

            title = str(payload.get("title", "")).strip()
            content = str(payload.get("content", "")).strip()
            if not title or not content:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "title and content are required"})
                return True
            try:
                record = ingest_raw(
                    title,
                    content,
                    url=str(payload.get("url", "")).strip(),
                    source_type=str(payload.get("source_type", "page")).strip(),
                    metadata=payload.get("metadata"),
                )
                self._send_json(HTTPStatus.OK, {"ok": True, "raw": record})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return True

        if path == "/wiki/compile":
            max_sources = int(payload.get("max_sources", 3))
            try:
                result = compile_wiki(max_sources=max_sources)
                self._send_json(HTTPStatus.OK, result)
            except RuntimeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return True

        if path == "/wiki/health-check":
            try:
                result = health_check()
                self._send_json(HTTPStatus.OK, result)
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return True

        return False

    def _serve_web_app(self, path: str) -> bool:
        if path == "/app":
            path = "/app/"
        if not path.startswith("/app/"):
            return False

        rel = unquote(path[len("/app/") :]).lstrip("/")
        if not rel or rel.endswith("/"):
            rel = "index.html"

        target = (_WEB_ROOT / rel).resolve()
        if not str(target).startswith(str(_WEB_ROOT.resolve())):
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
            return True
        if not target.exists() or not target.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return True

        mime, _ = mimetypes.guess_type(str(target))
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)
        return True
