from __future__ import annotations

import base64
import io
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

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
    return {
        "author": "",
        "date": "",
        "category": "",
        "medium": "",
        "tldr": "",
        "thoughts": "",
        "notes": "",
        "tags": [],
        "custom": [],
    }


def _normalize_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    meta = _empty_metadata()
    if not raw:
        return meta
    meta["author"] = str(raw.get("author", "") or "").strip()
    meta["date"] = str(raw.get("date", "") or "").strip()
    meta["category"] = str(raw.get("category", "") or "").strip()
    meta["medium"] = str(raw.get("medium", "") or "").strip()
    meta["tldr"] = str(raw.get("tldr", "") or "").strip()
    meta["thoughts"] = str(raw.get("thoughts", "") or "").strip()
    meta["notes"] = str(raw.get("notes", "") or "").strip()
    tags: list[str] = []
    for item in raw.get("tags") or []:
        tag = str(item or "").strip()
        if tag and tag not in tags:
            tags.append(tag)
    meta["tags"] = tags[:40]
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


def _canonical_page_url(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    value = value.split("#", 1)[0]
    if value.endswith("/") and value.count("/") > 2:
        value = value.rstrip("/")
    return value


def _urls_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    return _canonical_page_url(left) == _canonical_page_url(right)


def _generate_summary(page: dict[str, Any]) -> str:
    block = render_page_context(page)
    if len(block) > 4500:
        block = block[:4500]
    messages = [
        {
            "role": "user",
            "content": (
                "Summarize this page in 3-5 short bullet points for future reference. "
                "Focus on what matters and what the reader should remember.\n\n"
                f"{block}"
            ),
        }
    ]
    try:
        return str(provider_chat(messages, stream=False, max_tokens=400)).strip()
    except Exception:
        title = page.get("title", "Untitled")
        return f"Saved page: {title}"


def _instant_summary(page: dict[str, Any]) -> str:
    bullets: list[str] = []
    for heading in page.get("headings") or []:
        text = str(heading or "").strip()
        if text:
            bullets.append(f"- {text}")
        if len(bullets) >= 4:
            break
    if not bullets:
        for para in page.get("paragraphs") or []:
            text = str(para or "").strip()
            if len(text) < 40:
                continue
            clipped = text[:180].rstrip()
            bullets.append(f"- {clipped}{'…' if len(text) > 180 else ''}")
            if len(bullets) >= 3:
                break
    if bullets:
        return "\n".join(bullets)
    return f"Saved page: {page.get('title', 'Untitled')}"


def _persist_summary(page_id: str, summary: str) -> None:
    path = _page_path(page_id)
    if not path.exists():
        return
    page = json.loads(path.read_text(encoding="utf-8"))
    page["summary"] = summary
    path.write_text(json.dumps(page, indent=2), encoding="utf-8")
    index = _load_saved_index()
    for entry in index:
        if entry.get("id") == page_id:
            entry["summary"] = summary
            break
    _save_saved_index(index)


def _enrich_saved_page(page_id: str, record: dict[str, Any]) -> None:
    try:
        summary = _generate_summary(record)
        if not _page_path(page_id).exists():
            return
        _persist_summary(page_id, summary)
        ingest_text(
            text=f"Saved page: {record.get('title', '')}\nURL: {record.get('url', '')}\n\n{summary}",
            source="saved_page",
            metadata={
                "page_id": page_id,
                "url": record.get("url", ""),
                "title": record.get("title", ""),
            },
            flagged_important=True,
        )
    except Exception:
        pass


def save_page(
    page_data: dict[str, Any],
    chat_history: list[dict[str, str]] | None = None,
    *,
    background: bool = False,
) -> dict[str, Any]:
    """Explicitly save a page. LLM summary and memory ingest can run in the background."""
    _ensure_dirs()
    url = str(page_data.get("url", "")).strip()
    title = str(page_data.get("title", "")).strip() or "Untitled page"
    index = _load_saved_index()

    existing = next((e for e in index if e.get("url") == url and url), None)
    page_id = existing["id"] if existing else str(uuid.uuid4())
    saved_at = _now_iso()
    prior_meta: dict[str, Any] = {}
    prior_summary = ""
    if existing:
        prior = get_saved_page(page_id)
        if prior:
            prior_meta = prior.get("metadata") or {}
            prior_summary = str(prior.get("summary") or "").strip()

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
        "summary": prior_summary or _instant_summary(
            {
                "title": title,
                "headings": page_data.get("headings", []),
                "paragraphs": page_data.get("paragraphs", []),
            }
        ),
    }

    _page_path(page_id).write_text(json.dumps(record, indent=2), encoding="utf-8")

    if chat_history:
        save_chat_history(page_id, chat_history)

    quotes = _load_quotes()
    quotes_changed = False
    for quote in quotes:
        if _urls_match(quote.get("page_url", ""), url) and not quote.get("page_id"):
            quote["page_id"] = page_id
            quotes_changed = True
    if quotes_changed:
        _save_quotes(quotes)

    summary_entry = {
        "id": page_id,
        "url": url,
        "title": title,
        "site": record["site"],
        "summary": record["summary"],
        "saved_at": saved_at,
        "updated_at": saved_at,
        "quote_count": len([q for q in quotes if q.get("page_id") == page_id]),
    }
    index = [e for e in index if e.get("id") != page_id]
    index.insert(0, summary_entry)
    _save_saved_index(index)

    if background:
        threading.Thread(
            target=_enrich_saved_page,
            args=(page_id, dict(record)),
            daemon=True,
        ).start()
    else:
        _enrich_saved_page(page_id, record)
        path = _page_path(page_id)
        if path.exists():
            record["summary"] = json.loads(path.read_text(encoding="utf-8")).get(
                "summary", record["summary"]
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

    from core.memory.buckets_service import forget_library_page
    forget_library_page(page_id)

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
    quotes = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for quote in quotes:
        if not quote.get("id"):
            quote["id"] = str(uuid.uuid4())
            changed = True
    if changed:
        _save_quotes(quotes)
    return quotes


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
    quote_id = (quote_id or "").strip()
    quotes = _load_quotes()
    match = next((q for q in quotes if str(q.get("id", "")).strip() == quote_id), None)
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
    quote_id = (quote_id or "").strip()
    if not quote_id:
        return False
    quotes = _load_quotes()
    kept = [q for q in quotes if str(q.get("id", "")).strip() != quote_id]
    if len(kept) == len(quotes):
        return False
    _save_quotes(kept)

    index = _load_saved_index()
    for entry in index:
        pid = entry.get("id")
        if pid:
            entry["quote_count"] = len([q for q in kept if q.get("page_id") == pid])
    _save_saved_index(index)
    from core.memory.buckets_service import forget_library_quote
    forget_library_quote(quote_id)
    return True


def get_quote(quote_id: str) -> dict[str, Any] | None:
    quote_id = (quote_id or "").strip()
    if not quote_id:
        return None
    return next((q for q in _load_quotes() if str(q.get("id", "")).strip() == quote_id), None)


def list_quotes(page_id: str = "", page_url: str = "", limit: int = 100) -> list[dict[str, Any]]:
    quotes = _load_quotes()
    if page_id and page_url:
        quotes = [
            q for q in quotes
            if q.get("page_id") == page_id or _urls_match(q.get("page_url", ""), page_url)
        ]
    elif page_id:
        quotes = [q for q in quotes if q.get("page_id") == page_id]
    elif page_url:
        quotes = [q for q in quotes if _urls_match(q.get("page_url", ""), page_url)]
    return quotes[:limit]


def explore_suggestions(page: dict[str, Any]) -> list[dict[str, str]]:
    title = str(page.get("title", "Untitled")).strip() or "this topic"
    url = str(page.get("url", "")).strip()
    headings = ", ".join(str(h) for h in page.get("headings", [])[:6])
    page_links = _explore_links_from_page(page)
    link_preview = "\n".join(
        f"- {item['title']}: {item['url']}" for item in page_links[:8]
    ) or "(none)"
    messages = [
        {
            "role": "user",
            "content": (
                f"Title: {title}\nURL: {url}\nTopics: {headings}\n"
                f"On-page links:\n{link_preview}\n\n"
                "Return JSON only: an array of exactly 10 further-reading items "
                '[{"title":"...","url":"https://...","why":"one sentence"}].\n'
                "These are links a curious reader should open next. Prefer real URLs "
                "(Wikipedia, papers, docs, reputable articles). Reuse strong on-page "
                "links when useful. No markdown, no numbering."
            ),
        }
    ]
    try:
        raw = str(provider_chat(messages, stream=False, max_tokens=700)).strip()
        items = _parse_explore_items(raw)
    except Exception:
        items = []
    merged = _dedupe_explore_items([*items, *page_links, *_fallback_explore_links(title, url)])
    return merged[:10] or _fallback_explore_links(title, url)[:10]


def _explore_links_from_page(page: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for link in page.get("links") or []:
        if not isinstance(link, dict):
            continue
        href = str(link.get("href") or link.get("url") or "").strip()
        label = str(link.get("text") or link.get("title") or "").strip()
        if href.startswith("http"):
            items.append({"title": label or href, "url": href})
    return _dedupe_explore_items(items)


def _fallback_explore_links(title: str, url: str = "") -> list[dict[str, str]]:
    query = quote_plus(title or "related reading")
    host = ""
    try:
        host = urlparse(url).netloc
    except Exception:
        host = ""
    items = [
        {"title": f"Wikipedia: {title}", "url": f"https://en.wikipedia.org/w/index.php?search={query}", "why": "Background and related entries for this topic."},
        {"title": f"Search the web: {title}", "url": f"https://www.google.com/search?q={query}", "why": "A wider sweep of articles and essays on the same ideas."},
        {"title": f"Scholar: {title}", "url": f"https://scholar.google.com/scholar?q={query}", "why": "Papers and citations if you want the research trail."},
        {"title": f"Videos: {title}", "url": f"https://www.youtube.com/results?search_query={query}", "why": "Talks and explainers that unpack the same questions."},
        {"title": f"Discussions: {title}", "url": f"https://www.reddit.com/search/?q={query}", "why": "How other readers argue with or extend this piece."},
        {"title": f"News: {title}", "url": f"https://news.google.com/search?q={query}", "why": "Current coverage connected to the topic."},
    ]
    if host:
        items.insert(0, {"title": f"More from {host}", "url": f"https://{host}"})
    return items


def _parse_explore_items(raw: str) -> list[dict[str, str]]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("[")
    end = text.rfind("]")
    payload = text[start : end + 1] if start >= 0 and end > start else text
    parsed: Any
    try:
        parsed = json.loads(payload)
    except Exception:
        parsed = None
    items: list[dict[str, str]] = []
    if isinstance(parsed, list):
        for entry in parsed:
            if isinstance(entry, dict):
                title = str(entry.get("title") or "").strip()
                href = str(entry.get("url") or entry.get("href") or "").strip()
                if href.startswith("http"):
                    why = str(entry.get("why") or entry.get("blurb") or "").strip()
                    items.append({"title": title or href, "url": href, **({"why": why} if why else {})})
            elif isinstance(entry, str):
                items.extend(_explore_item_from_line(entry))
    else:
        for line in text.splitlines():
            items.extend(_explore_item_from_line(line))
    return _dedupe_explore_items(items)


def _explore_item_from_line(line: str) -> list[dict[str, str]]:
    cleaned = str(line or "").strip().lstrip("0123456789.-) ")
    if not cleaned:
        return []
    match = None
    for token in cleaned.split():
        if token.startswith("http://") or token.startswith("https://"):
            match = token.strip("<>),.")
            break
    if not match:
        return []
    title = cleaned.replace(match, "").replace("—", " ").replace("-", " ").strip(" :|-")
    return [{"title": title or match, "url": match}]


def _dedupe_explore_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in items:
        href = str(item.get("url") or "").strip()
        if not href.startswith("http"):
            continue
        key = href.split("#", 1)[0].rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append({
            "title": str(item.get("title") or href).strip()[:120],
            "url": href,
            **({"why": str(item.get("why") or "").strip()} if str(item.get("why") or "").strip() else {}),
        })
    return unique


def _default_explore_suggestions(page: dict[str, Any] | None = None) -> list[dict[str, str]]:
    page = page or {}
    title = str(page.get("title", "this topic")).strip() or "this topic"
    return _dedupe_explore_items([
        *_explore_links_from_page(page),
        *_fallback_explore_links(title, str(page.get("url", "")).strip()),
    ])[:10]


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
    from core.memory.buckets_service import forget_all_library_events
    forget_all_library_events()


def find_saved_page_by_url(url: str) -> dict[str, Any] | None:
    exact = None
    canonical = None
    needle = _canonical_page_url(url)
    for entry in _load_saved_index():
        entry_url = str(entry.get("url", "")).strip()
        if entry_url == url:
            exact = entry
            break
        if needle and not canonical and _canonical_page_url(entry_url) == needle:
            canonical = entry
    match = exact or canonical
    if not match:
        return None
    return get_saved_page(match["id"])
