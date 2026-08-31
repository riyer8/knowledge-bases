from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.config import config
from core.ingestion.pipeline import ingest_text
from core.llm_providers import chat as provider_chat
from core.memory.concept_graph import list_concepts, remember_concept, related_for_page
from core.memory.graph import load_graph
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
    return quote


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
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen_nodes: set[str] = set()

    def add_node(node_id: str, label: str, node_type: str, meta: dict | None = None) -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        nodes.append({"id": node_id, "label": label[:80], "type": node_type, **(meta or {})})

    for page in list_saved_pages(limit=50):
        pid = f"page:{page['id']}"
        add_node(pid, page.get("title", "Page"), "page", {"url": page.get("url")})
        for concept in related_for_page(page_url=page.get("url", ""), limit=5):
            cid = concept.get("id", "")
            if cid:
                add_node(cid, concept.get("name", "Concept"), "concept")
                edges.append({"source": pid, "target": cid})

    for concept in list_concepts(limit=30):
        cid = concept.get("id", "")
        if cid:
            add_node(cid, concept.get("name", "Concept"), "concept")

    for quote in list_quotes(limit=40):
        qid = f"quote:{quote['id']}"
        add_node(qid, quote.get("text", "")[:60] + "…", "quote")
        if quote.get("page_id"):
            pid = f"page:{quote['page_id']}"
            add_node(pid, quote.get("page_title", "Page"), "page")
            edges.append({"source": qid, "target": pid})

    adjacency = load_graph()
    for source, neighbors in adjacency.items():
        if source.startswith("concept:"):
            add_node(source, source.replace("concept:", ""), "concept")
        for target in neighbors:
            if target.startswith("concept:"):
                add_node(target, target.replace("concept:", ""), "concept")
                edges.append({"source": source, "target": target})

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
