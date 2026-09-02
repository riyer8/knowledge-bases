from __future__ import annotations

from http import HTTPStatus

from core.library_service import (
    clear_library,
    delete_quote,
    delete_saved_page,
    explore_suggestions,
    extract_document_context,
    find_saved_page_by_url,
    get_saved_page,
    graph_visual,
    list_quotes,
    list_saved_pages,
    save_page as library_save_page,
    save_quote,
    update_page,
    update_quote,
)


class LibraryRoutesMixin:
    def handle_library_patch(self, path: str, payload: dict) -> bool:
        if path.startswith("/library/pages/"):
            page_id = path.split("/library/pages/", 1)[1].strip("/")
            if not page_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "page id required"})
                return True
            title = payload.get("title")
            metadata = payload.get("metadata")
            if title is not None:
                title = str(title).strip()
            if title is None and metadata is None:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "title or metadata is required"})
                return True
            try:
                page = update_page(page_id, title=title, metadata=metadata)
                self._send_json(HTTPStatus.OK, {"ok": True, "page": page})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return True

        if path.startswith("/library/quotes/"):
            quote_id = path.split("/library/quotes/", 1)[1].strip("/")
            if not quote_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "quote id required"})
                return True
            text = payload.get("text")
            note = payload.get("note")
            if text is not None:
                text = str(text).strip()
            if text is None and note is None:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "text or note is required"})
                return True
            try:
                quote = update_quote(quote_id, text=text, note=note)
                self._send_json(HTTPStatus.OK, {"ok": True, "quote": quote})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return True

        return False

    def handle_library_delete(self, path: str) -> bool:
        if path.startswith("/library/pages/"):
            page_id = path.split("/library/pages/", 1)[1].strip("/")
            if not page_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "page id required"})
                return True
            deleted = delete_saved_page(page_id)
            if not deleted:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "page not found"})
                return True
            self._send_json(HTTPStatus.OK, {"ok": True})
            return True

        if path.startswith("/library/quotes/"):
            quote_id = path.split("/library/quotes/", 1)[1].strip("/")
            if not quote_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "quote id required"})
                return True
            deleted = delete_quote(quote_id)
            if not deleted:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "quote not found"})
                return True
            self._send_json(HTTPStatus.OK, {"ok": True})
            return True

        return False

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
            if path == "/library/extract-document":
                try:
                    page = extract_document_context(
                        url=str(payload.get("url", "")).strip(),
                        content_base64=str(payload.get("content_base64", "")).strip(),
                        title=str(payload.get("title", "")).strip(),
                    )
                    self._send_json(HTTPStatus.OK, {"ok": True, "page": page})
                except ValueError as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                except Exception as exc:
                    self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
                return
            if path == "/library/clear":
                clear_library()
                self._send_json(HTTPStatus.OK, {"ok": True, "scope": "library"})
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
