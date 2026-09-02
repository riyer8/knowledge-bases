from __future__ import annotations

import base64
import io
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.config import config
from core.ingestion.pipeline import ingest_text
from core.llm_providers import chat as provider_chat
from core.memory.concept_graph import remember_concept, related_for_page
from core.memory.store import query as memory_query
from core.page_context_service import render_page_context

_LIBRARY_DIR_NAME = "library"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _library_dir() -> Path:
    return config.kb_root / _LIBRARY_DIR_NAME


def _saved_index_path() -> Path:
    return _library_dir() / "saved_pages.json"


def _page_path(page_id: str) -> Path:
    return _library_dir() / "pages" / f"{page_id}.json"


def _chat_path(page_id: str) -> Path:
    return _library_dir() / "chats" / f"{page_id}.jsonl"


def _quotes_path() -> Path:
    return _library_dir() / "quotes.json"


def _ensure_dirs() -> None:
    (_library_dir() / "pages").mkdir(parents=True, exist_ok=True)
    (_library_dir() / "chats").mkdir(parents=True, exist_ok=True)


def _load_saved_index() -> list[dict[str, Any]]:
    path = _saved_index_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_saved_index(entries: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    entries.sort(key=lambda e: e.get("saved_at", ""), reverse=True)
    _saved_index_path().write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _empty_metadata() -> dict[str, Any]:
    return {"author": "", "date": "", "custom": []}


def _normalize_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    meta = _empty_metadata()
    if not raw:
        return meta
    meta["author"] = str(raw.get("author", "") or "").strip()
    meta["date"] = str(raw.get("date", "") or "").strip()
    custom: list[dict[str, str]] = []
    for item in raw.get("custom") or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        value = str(item.get("value", "")).strip()
        if key:
            custom.append({"key": key, "value": value})
    meta["custom"] = custom[:30]
    return meta


def _metadata_from_pdf(reader) -> dict[str, Any]:
    info = getattr(reader, "metadata", None)
    if not info:
        return _empty_metadata()
    author = ""
    date = ""
    custom: list[dict[str, str]] = []
    for key, value in (info or {}).items():
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        lowered = key.lower().lstrip("/")
        if lowered in {"author", "creator"} and not author:
            author = text
        elif lowered in {"creationdate", "moddate"} and not date:
            date = text[:40]
        elif lowered == "title":
            custom.append({"key": "PDF title", "value": text})
        elif lowered == "subject" and text:
            custom.append({"key": "Subject", "value": text})
    return _normalize_metadata({"author": author, "date": date, "custom": custom})


def _site_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def _generate_summary(page: dict[str, Any]) -> str:
    block = render_page_context(page)
    messages = [
        {
            "role": "user",
            "content": (
                "Summarize this page in 3-5 bullet points for future reference. "
                "Focus on what matters and what the reader should remember.\n\n"
                f"{block}"
            ),
        }
    ]
    try:
        return str(provider_chat(messages, stream=False)).strip()
    except Exception:
        title = page.get("title", "Untitled")
        return f"Saved page: {title}"


def save_page(
    page_data: dict[str, Any],
    chat_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Explicitly save a page with summary and optional chat history."""
    _ensure_dirs()
    url = str(page_data.get("url", "")).strip()
    title = str(page_data.get("title", "")).strip() or "Untitled page"
    index = _load_saved_index()

    existing = next((e for e in index if e.get("url") == url and url), None)
    page_id = existing["id"] if existing else str(uuid.uuid4())
    saved_at = _now_iso()
    prior_meta: dict[str, Any] = {}
    if existing:
        prior = get_saved_page(page_id)
        if prior:
            prior_meta = prior.get("metadata") or {}

    record = {
        "id": page_id,
        "url": url,
        "title": title,
        "site": str(page_data.get("site", "")).strip() or _site_from_url(url),
        "headings": page_data.get("headings", [])[:50],
        "paragraphs": page_data.get("paragraphs", [])[:80],
        "code_blocks": page_data.get("code_blocks", [])[:20],
        "links": page_data.get("links", [])[:40],
        "selected_text": str(page_data.get("selected_text", ""))[:4000],
        "page_type": str(page_data.get("page_type", "webpage")),
        "visible_text": str(page_data.get("visible_text", ""))[:20000],
        "metadata": _normalize_metadata(page_data.get("metadata") or prior_meta),
        "saved_at": saved_at,
        "updated_at": saved_at,
    }
    record["summary"] = _generate_summary(record)

    _page_path(page_id).write_text(json.dumps(record, indent=2), encoding="utf-8")

    if chat_history:
        save_chat_history(page_id, chat_history)

    summary_entry = {
        "id": page_id,
        "url": url,
        "title": title,
        "site": record["site"],
        "summary": record["summary"],
        "saved_at": saved_at,
        "updated_at": saved_at,
        "quote_count": len([q for q in _load_quotes() if q.get("page_id") == page_id]),
    }
    index = [e for e in index if e.get("id") != page_id]
    index.insert(0, summary_entry)
    _save_saved_index(index)

    ingest_text(
        text=f"Saved page: {title}\nURL: {url}\n\n{record['summary']}",
        source="saved_page",
        metadata={"page_id": page_id, "url": url, "title": title},
        flagged_important=True,
    )
    return record


def list_saved_pages(limit: int = 100) -> list[dict[str, Any]]:
    return _load_saved_index()[: max(1, min(limit, 200))]


def get_saved_page(page_id: str) -> dict[str, Any] | None:
    path = _page_path(page_id)
    if not path.exists():
        return None
    page = json.loads(path.read_text(encoding="utf-8"))
    page["chat_history"] = load_chat_history(page_id)
    page["quotes"] = [q for q in _load_quotes() if q.get("page_id") == page_id]
    return page


def delete_saved_page(page_id: str) -> bool:
    page = get_saved_page(page_id)
    if not page:
        return False

    for path in (_page_path(page_id), _chat_path(page_id)):
        if path.exists():
            path.unlink()

    quotes = [q for q in _load_quotes() if q.get("page_id") != page_id]
    _save_quotes(quotes)

    index = [e for e in _load_saved_index() if e.get("id") != page_id]
    _save_saved_index(index)
    return True


def update_page(
    page_id: str,
    *,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update saved page title and/or metadata."""
    page = get_saved_page(page_id)
    if not page:
        raise ValueError("page not found")

    if title is not None:
        title = title.strip()
        if not title:
            raise ValueError("title is required")
        page["title"] = title

    if metadata is not None:
        page["metadata"] = _normalize_metadata(metadata)

    page["updated_at"] = _now_iso()
    _page_path(page_id).write_text(json.dumps(page, indent=2), encoding="utf-8")

    index = _load_saved_index()
    for entry in index:
        if entry.get("id") == page_id:
            if title is not None:
                entry["title"] = page["title"]
            entry["updated_at"] = page["updated_at"]
            break
    _save_saved_index(index)
    return page


def update_page_title(page_id: str, title: str) -> dict[str, Any]:
    return update_page(page_id, title=title)


def _extract_pdf_text(data: bytes, max_pages: int = 40) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        text = (page.extract_text() or "").strip()
        if text:
            chunks.append(text)
    return "\n\n".join(chunks)


def _pdf_metadata(data: bytes) -> dict[str, Any]:
    try:
        from pypdf import PdfReader

        return _metadata_from_pdf(PdfReader(io.BytesIO(data)))
    except Exception:
        return _empty_metadata()


def extract_document_context(
    *,
    url: str,
    content_base64: str = "",
    title: str = "",
) -> dict[str, Any]:
    """
    Build page context for PDFs and other documents the extension cannot read via DOM.
    """
    url = url.strip()
    if not url:
        raise ValueError("url is required")

    raw = b""
    if content_base64:
        raw = base64.b64decode(content_base64)
    elif url.lower().endswith(".pdf") or ".pdf?" in url.lower():
        import urllib.request

        with urllib.request.urlopen(url, timeout=20) as resp:
            raw = resp.read()

    if not raw:
        raise ValueError("document content is required")

    visible_text = _extract_pdf_text(raw)
    if not visible_text.strip():
        raise ValueError("could not extract text from document")

    paragraphs = [
        p.strip()
        for p in visible_text.split("\n\n")
        if len(p.strip()) > 40
    ][:80]

    display_title = title.strip() or _title_from_url(url)
    pdf_meta = _pdf_metadata(raw)
    return {
        "url": url,
        "title": display_title,
        "site": _site_from_url(url) or "document",
        "headings": [],
        "paragraphs": paragraphs,
        "code_blocks": [],
        "links": [],
        "images": [],
        "tables": [],
        "selected_text": "",
        "page_type": "pdf",
        "visible_text": visible_text[:20000],
        "metadata": pdf_meta,
    }


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    name = path.split("/")[-1] if path else "Document"
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name.replace("-", " ").replace("_", " ").strip() or "PDF document"


def save_chat_history(page_id: str, history: list[dict[str, str]]) -> None:
    _ensure_dirs()
    path = _chat_path(page_id)
    lines = []
    for turn in history:
        role = str(turn.get("role", "")).strip()
        content = str(turn.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            lines.append(json.dumps({"role": role, "content": content, "at": _now_iso()}))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def append_chat_turn(page_id: str, role: str, content: str) -> None:
    history = load_chat_history(page_id)
    history.append({"role": role, "content": content})
    save_chat_history(page_id, history)


def load_chat_history(page_id: str) -> list[dict[str, str]]:
    path = _chat_path(page_id)
    if not path.exists():
        return []
    history: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            turn = json.loads(line)
            history.append({"role": turn.get("role", ""), "content": turn.get("content", "")})
        except json.JSONDecodeError:
            continue
    return history


def _load_quotes() -> list[dict[str, Any]]:
    path = _quotes_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_quotes(quotes: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    _quotes_path().write_text(json.dumps(quotes, indent=2), encoding="utf-8")


def save_quote(
    *,
    text: str,
    page_id: str = "",
    page_url: str = "",
    page_title: str = "",
    note: str = "",
) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("text is required")

    quote_id = str(uuid.uuid4())
    quote = {
        "id": quote_id,
        "text": text.strip()[:4000],
        "note": note.strip(),
        "page_id": page_id,
        "page_url": page_url,
        "page_title": page_title,
        "saved_at": _now_iso(),
    }
    quotes = _load_quotes()
    quotes.insert(0, quote)
    _save_quotes(quotes[:500])

    if page_id:
        index = _load_saved_index()
        for entry in index:
            if entry.get("id") == page_id:
                entry["quote_count"] = len([q for q in quotes if q.get("page_id") == page_id])
                entry["updated_at"] = _now_iso()
                break
        _save_saved_index(index)

    def _index_in_background() -> None:
        try:
            if page_id:
                remember_concept(
                    passage=text.strip(),
                    page_id=page_id,
                    page_title=page_title or "Saved quote",
                    page_url=page_url,
                    note=note,
                    event_id="",
                )
            ingest_text(
                text=f'Quote from "{page_title}":\n{text.strip()}\n{("Note: " + note) if note else ""}',
                source="saved_quote",
                metadata={"quote_id": quote_id, "page_id": page_id, "url": page_url},
                flagged_important=True,
            )
        except Exception:
            pass

    threading.Thread(target=_index_in_background, daemon=True).start()
    return quote


def update_quote(
    quote_id: str,
    *,
    text: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    quotes = _load_quotes()
    match = next((q for q in quotes if q.get("id") == quote_id), None)
    if not match:
        raise ValueError("quote not found")

    if text is not None:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("text is required")
        match["text"] = cleaned[:4000]
    if note is not None:
        match["note"] = note.strip()
    match["updated_at"] = _now_iso()
    _save_quotes(quotes)
    return match


def delete_quote(quote_id: str) -> bool:
    quotes = _load_quotes()
    kept = [q for q in quotes if q.get("id") != quote_id]
    if len(kept) == len(quotes):
        return False
    _save_quotes(kept)

    page_ids = {q.get("page_id") for q in kept if q.get("page_id")}
    index = _load_saved_index()
    for entry in index:
        pid = entry.get("id")
        if pid:
            entry["quote_count"] = len([q for q in kept if q.get("page_id") == pid])
    _save_saved_index(index)
    return True


def list_quotes(page_id: str = "", page_url: str = "", limit: int = 100) -> list[dict[str, Any]]:
    quotes = _load_quotes()
    if page_id and page_url:
        quotes = [
            q for q in quotes
            if q.get("page_id") == page_id or q.get("page_url") == page_url
        ]
    elif page_id:
        quotes = [q for q in quotes if q.get("page_id") == page_id]
    elif page_url:
        quotes = [q for q in quotes if q.get("page_url") == page_url]
    return quotes[:limit]


def explore_suggestions(page: dict[str, Any]) -> list[str]:
    title = str(page.get("title", "Untitled")).strip()
    url = str(page.get("url", "")).strip()
    headings = ", ".join(str(h) for h in page.get("headings", [])[:4])
    snippet = str(page.get("visible_text", ""))[:600]
    messages = [
        {
            "role": "user",
            "content": (
                f"Title: {title}\nURL: {url}\nTopics: {headings}\nSnippet: {snippet}\n\n"
                "Suggest exactly 5 lightweight next steps for a curious reader. "
                "Mix: 2 related articles or sites (include real URLs when confident), "
                "2 deeper topics to search, and 1 question to ask. "
                "One suggestion per line, under 18 words each, no numbering."
            ),
        }
    ]
    try:
        raw = str(provider_chat(messages, stream=False, max_tokens=220)).strip()
        lines = [line.strip().lstrip("0123456789.-) ") for line in raw.splitlines() if line.strip()]
        return lines[:5] if lines else _default_explore_suggestions()
    except Exception:
        return _default_explore_suggestions()


def _default_explore_suggestions() -> list[str]:
    return [
        "Search for a recent article on the main topic",
        "Read the Wikipedia overview for background",
        "What is the strongest counterargument?",
        "Quiz me to check my understanding",
        "What should I read next to go deeper?",
    ]


def graph_visual() -> dict[str, Any]:
    """Page-centric graph: saved pages linked by shared concepts (no quote nodes)."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen_nodes: set[str] = set()
    page_concepts: dict[str, set[str]] = {}

    def add_node(node_id: str, label: str, node_type: str, meta: dict | None = None) -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        nodes.append({"id": node_id, "label": label, "type": node_type, **(meta or {})})

    pages = list_saved_pages(limit=50)
    for page in pages:
        pid = f"page:{page['id']}"
        add_node(
            pid,
            page.get("title", "Page"),
            "page",
            {
                "url": page.get("url"),
                "quote_count": int(page.get("quote_count", 0) or 0),
            },
        )
        concept_ids: set[str] = set()
        for concept in related_for_page(page_url=page.get("url", ""), limit=8):
            cid = concept.get("id", "")
            if cid:
                concept_ids.add(cid)
        page_concepts[pid] = concept_ids

    page_ids = list(page_concepts.keys())
    for i, left in enumerate(page_ids):
        for right in page_ids[i + 1 :]:
            if page_concepts[left] & page_concepts[right]:
                edges.append({"source": left, "target": right, "type": "shared_topic"})

    return {"nodes": nodes, "edges": edges}


def clear_library() -> None:
    lib = _library_dir()
    if lib.exists():
        import shutil
        shutil.rmtree(lib)


def find_saved_page_by_url(url: str) -> dict[str, Any] | None:
    for entry in _load_saved_index():
        if entry.get("url") == url:
            return get_saved_page(entry["id"])
    return None
