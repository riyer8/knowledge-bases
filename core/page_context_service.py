from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from core.config import config
from core.ingestion.pipeline import ingest_text
from core.memory.concept_graph import remember_concept, related_for_page
from core.memory.store import query as memory_query


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _index_path():
    return config.pages_dir / "index.json"


def _page_path(page_id: str):
    return config.pages_dir / f"{page_id}.json"


def _load_index() -> list[dict[str, Any]]:
    path = _index_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_index(entries: list[dict[str, Any]]) -> None:
    config.pages_dir.mkdir(parents=True, exist_ok=True)
    entries.sort(key=lambda e: e.get("captured_at", ""), reverse=True)
    _index_path().write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _site_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def save_page_context(data: dict[str, Any]) -> dict[str, Any]:
    """Persist structured page context. Upserts by URL when possible."""
    config.ensure_dirs()
    url = str(data.get("url", "")).strip()
    title = str(data.get("title", "")).strip()
    index = _load_index()

    existing = next((e for e in index if e.get("url") == url and url), None)
    page_id = existing["id"] if existing else str(uuid.uuid4())
    captured_at = _now_iso()

    record = {
        "id": page_id,
        "url": url,
        "title": title,
        "site": str(data.get("site", "")).strip() or _site_from_url(url),
        "headings": data.get("headings", [])[:50],
        "paragraphs": data.get("paragraphs", [])[:80],
        "code_blocks": data.get("code_blocks", [])[:20],
        "links": data.get("links", [])[:40],
        "images": data.get("images", [])[:20],
        "tables": data.get("tables", [])[:10],
        "selected_text": str(data.get("selected_text", ""))[:4000],
        "page_type": str(data.get("page_type", "webpage")),
        "visible_text": str(data.get("visible_text", ""))[:20000],
        "captured_at": captured_at,
        "last_interacted_at": captured_at,
        "interaction_count": int(existing.get("interaction_count", 0) if existing else 0),
    }

    _page_path(page_id).write_text(json.dumps(record, indent=2), encoding="utf-8")

    summary = {
        "id": page_id,
        "url": url,
        "title": title,
        "site": record["site"],
        "captured_at": captured_at,
        "last_interacted_at": captured_at,
        "interaction_count": record["interaction_count"],
    }
    index = [e for e in index if e.get("id") != page_id]
    index.insert(0, summary)
    _save_index(index[:500])
    return record


def get_page(page_id: str) -> dict[str, Any] | None:
    path = _page_path(page_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_page_by_url(url: str) -> dict[str, Any] | None:
    for entry in _load_index():
        if entry.get("url") == url:
            return get_page(entry["id"])
    return None


def touch_page(page_id: str) -> None:
    page = get_page(page_id)
    if not page:
        return
    page["last_interacted_at"] = _now_iso()
    page["interaction_count"] = int(page.get("interaction_count", 0)) + 1
    _page_path(page_id).write_text(json.dumps(page, indent=2), encoding="utf-8")
    index = _load_index()
    for entry in index:
        if entry.get("id") == page_id:
            entry["last_interacted_at"] = page["last_interacted_at"]
            entry["interaction_count"] = page["interaction_count"]
            break
    _save_index(index)


def list_history(limit: int = 20) -> list[dict[str, Any]]:
    return _load_index()[: max(1, min(limit, 100))]


def remember_passage(
    page_id: str,
    selected_text: str,
    note: str = "",
) -> dict[str, Any]:
    page = get_page(page_id)
    if not page:
        raise ValueError(f"Unknown page id: {page_id}")
    if not selected_text.strip():
        raise ValueError("selected_text is required")

    title = page.get("title", "Untitled page")
    url = page.get("url", "")
    text = (
        f"Remembered from: {title}\n"
        f"URL: {url}\n"
        f"Passage: {selected_text.strip()}\n"
    )
    if note.strip():
        text += f"Note: {note.strip()}\n"

    event = ingest_text(
        text=text,
        source="browser_remember",
        metadata={
            "page_id": page_id,
            "url": url,
            "title": title,
            "selected_text": selected_text.strip(),
            "note": note.strip(),
        },
        flagged_important=True,
    )
    concept = remember_concept(
        passage=selected_text.strip(),
        page_id=page_id,
        page_title=title,
        page_url=url,
        note=note,
        event_id=str(event.get("id", "")),
    )
    touch_page(page_id)
    return {
        "ok": True,
        "event_id": event.get("id", ""),
        "page_id": page_id,
        "selected_text": selected_text.strip(),
        "note": note.strip(),
        "concept": {
            "id": concept.get("id"),
            "name": concept.get("name"),
            "understanding_score": concept.get("understanding_score"),
            "related_names": concept.get("related_names", []),
        },
    }


def search_pages(query: str, top_k: int = 8) -> list[dict[str, Any]]:
    """Semantic search over memory store, enriched with page metadata when available."""
    chunks = memory_query(query, top_k=top_k)
    results: list[dict[str, Any]] = []
    for chunk in chunks:
        meta = {}
        for page in _load_index():
            page_full = get_page(page["id"])
            if not page_full:
                continue
            if page_full.get("url") and page_full["url"] in chunk.text:
                meta = {"page_id": page["id"], "title": page_full.get("title"), "url": page_full.get("url")}
                break
        results.append({
            "event_id": chunk.event_id,
            "text": chunk.text,
            "source": chunk.source,
            "timestamp": chunk.timestamp,
            "score": None,
            "page": meta or None,
        })
    return results


def get_connections(url: str = "", query: str = "", top_k: int = 5) -> list[dict[str, Any]]:
    """Return related prior reading and concept graph matches."""
    concept_items = related_for_page(page_url=url, query=query, limit=top_k)
    connections: list[dict[str, Any]] = []

    for concept in concept_items:
        latest = (concept.get("sources") or [{}])[0]
        connections.append({
            "type": "concept",
            "concept_id": concept.get("id"),
            "name": concept.get("name"),
            "understanding_score": concept.get("understanding_score"),
            "text": latest.get("passage", concept.get("name", ""))[:400],
            "title": latest.get("title") or concept.get("name"),
            "url": latest.get("url"),
            "timestamp": concept.get("last_encountered"),
        })

    seed = query.strip()
    if not seed and url:
        page = get_page_by_url(url)
        if page:
            seed = f"{page.get('title', '')} {page.get('visible_text', '')[:1500]}"
        else:
            seed = url

    if seed:
        chunks = memory_query(seed, top_k=top_k)
        seen: set[str] = set()
        for chunk in chunks:
            key = chunk.event_id
            if key in seen:
                continue
            seen.add(key)
            title = None
            page_url = None
            for entry in _load_index():
                full = get_page(entry["id"])
                if full and full.get("url") and full["url"] in chunk.text:
                    title = full.get("title")
                    page_url = full.get("url")
                    break
            connections.append({
                "type": "memory",
                "event_id": chunk.event_id,
                "text": chunk.text[:400],
                "source": chunk.source,
                "timestamp": chunk.timestamp,
                "title": title,
                "url": page_url,
            })

    return connections[:top_k]


def render_page_context(page: dict[str, Any]) -> str:
    parts = [
        f"Title: {page.get('title', '')}",
        f"URL: {page.get('url', '')}",
        f"Site: {page.get('site', '')}",
        f"Page type: {page.get('page_type', 'webpage')}",
    ]
    headings = page.get("headings") or []
    if headings:
        parts.append("Headings:\n" + "\n".join(f"- {h}" for h in headings[:20]))
    selected = str(page.get("selected_text", "")).strip()
    if selected:
        parts.append(f"Selected text:\n{selected}")
    visible = str(page.get("visible_text", "")).strip()
    if visible:
        parts.append(f"Visible text:\n{visible[:12000]}")
    return "\n\n".join(parts)
