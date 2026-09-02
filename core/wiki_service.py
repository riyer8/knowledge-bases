"""LLM-maintained markdown wiki — raw sources compiled into linked articles."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import config
from core.llm_providers import chat as provider_chat

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _wiki_dir() -> Path:
    return config.kb_root / "wiki"


def _raw_dir() -> Path:
    return config.wiki_raw_dir


def _articles_dir() -> Path:
    return config.wiki_articles_dir


def _outputs_dir() -> Path:
    return config.wiki_outputs_dir


def _index_path() -> Path:
    return _wiki_dir() / "index.md"


def _manifest_path() -> Path:
    return _wiki_dir() / "manifest.json"


def _ensure_dirs() -> None:
    config.ensure_dirs()
    _raw_dir().mkdir(parents=True, exist_ok=True)
    _articles_dir().mkdir(parents=True, exist_ok=True)
    _outputs_dir().mkdir(parents=True, exist_ok=True)
    if not _index_path().exists():
        _index_path().write_text(
            "# Knowledge Wiki\n\n_Auto-maintained index. Run **Compile** to update from raw sources._\n",
            encoding="utf-8",
        )
    if not _manifest_path().exists():
        _manifest_path().write_text(
            json.dumps({"compiled_raw_ids": [], "last_compile": None, "last_health_check": None}, indent=2),
            encoding="utf-8",
        )


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:80] or "untitled"


def _load_manifest() -> dict[str, Any]:
    _ensure_dirs()
    return json.loads(_manifest_path().read_text(encoding="utf-8"))


def _save_manifest(data: dict[str, Any]) -> None:
    _wiki_dir().mkdir(parents=True, exist_ok=True)
    _manifest_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    header = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, str] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta, body


def _build_frontmatter(meta: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if value is None:
            continue
        text = str(value).replace("\n", " ").strip()
        lines.append(f'{key}: "{text}"')
    lines.append("---\n")
    return "\n".join(lines)


def ingest_raw(
    title: str,
    content: str,
    *,
    url: str = "",
    source_type: str = "page",
    page_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Save a source document into wiki/raw/ as markdown."""
    _ensure_dirs()
    title = (title or "Untitled").strip()
    content = (content or "").strip()
    if not content:
        raise ValueError("content is required")

    raw_id = uuid.uuid4().hex[:12]
    slug = slugify(title)
    filename = f"{slug}-{raw_id[:6]}.md"
    path = _raw_dir() / filename

    meta = {
        "id": raw_id,
        "title": title,
        "url": url,
        "source_type": source_type,
        "page_id": page_id,
        "ingested_at": _now_iso(),
    }
    if metadata:
        for key in ("author", "date"):
            if metadata.get(key):
                meta[key] = str(metadata[key])

    body = f"# {title}\n\n"
    if url:
        body += f"Source: {url}\n\n"
    body += content

    path.write_text(_build_frontmatter(meta) + body, encoding="utf-8")
    return {"id": raw_id, "title": title, "url": url, "path": str(path), "filename": filename}


def ingest_from_saved_page(page: dict[str, Any]) -> dict[str, Any]:
    """Convert a saved library page into a wiki raw source."""
    text_parts = []
    if page.get("summary"):
        text_parts.append(f"## Summary\n\n{page['summary']}")
    visible = page.get("visible_text") or page.get("text") or ""
    if visible:
        text_parts.append(f"## Content\n\n{visible[:12000]}")
    for quote in page.get("quotes") or []:
        if isinstance(quote, dict) and quote.get("text"):
            note = quote.get("note", "")
            text_parts.append(f"> {quote['text']}\n>\n> _{note}_" if note else f"> {quote['text']}")

    content = "\n\n".join(text_parts).strip()
    if not content:
        raise ValueError("page has no content to ingest")

    return ingest_raw(
        title=str(page.get("title") or "Untitled"),
        content=content,
        url=str(page.get("url") or ""),
        source_type="saved_page",
        page_id=str(page.get("id") or ""),
        metadata=page.get("metadata"),
    )


def list_raw(limit: int = 100) -> list[dict[str, Any]]:
    _ensure_dirs()
    entries: list[dict[str, Any]] = []
    manifest = _load_manifest()
    compiled = set(manifest.get("compiled_raw_ids") or [])

    for path in sorted(_raw_dir().glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = path.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(text)
        raw_id = meta.get("id", path.stem)
        entries.append({
            "id": raw_id,
            "title": meta.get("title", path.stem),
            "url": meta.get("url", ""),
            "source_type": meta.get("source_type", "page"),
            "ingested_at": meta.get("ingested_at", ""),
            "filename": path.name,
            "compiled": raw_id in compiled,
        })
        if len(entries) >= limit:
            break
    return entries


def get_raw(raw_id: str) -> dict[str, Any] | None:
    _ensure_dirs()
    for path in _raw_dir().glob("*.md"):
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        if meta.get("id") == raw_id or path.stem.startswith(raw_id):
            return {
                "id": meta.get("id", raw_id),
                "title": meta.get("title", path.stem),
                "url": meta.get("url", ""),
                "content": body.strip(),
                "metadata": meta,
                "filename": path.name,
            }
    return None


def list_articles(limit: int = 200) -> list[dict[str, Any]]:
    _ensure_dirs()
    articles: list[dict[str, Any]] = []
    for path in sorted(_articles_dir().glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        excerpt = body.strip().replace("\n", " ")[:180]
        articles.append({
            "slug": path.stem,
            "title": meta.get("title", path.stem.replace("-", " ").title()),
            "updated_at": meta.get("updated_at", ""),
            "excerpt": excerpt,
            "backlinks": _extract_wikilinks(body),
        })
        if len(articles) >= limit:
            break
    return articles


def get_article(slug: str) -> dict[str, Any] | None:
    _ensure_dirs()
    path = _articles_dir() / f"{slug}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    return {
        "slug": slug,
        "title": meta.get("title", slug.replace("-", " ").title()),
        "content": body.strip(),
        "metadata": meta,
        "backlinks": _extract_wikilinks(body),
    }


def read_index() -> str:
    _ensure_dirs()
    return _index_path().read_text(encoding="utf-8")


def _extract_wikilinks(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\[\[([^\]]+)\]\]", text)))


def search_wiki(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    _ensure_dirs()
    q = query.lower().strip()
    if not q:
        return []

    hits: list[dict[str, Any]] = []
    for kind, directory in (("article", _articles_dir()), ("raw", _raw_dir())):
        for path in directory.glob("*.md"):
            text = path.read_text(encoding="utf-8").lower()
            if q not in text and q not in path.stem.lower():
                continue
            meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
            title = meta.get("title", path.stem)
            hits.append({
                "type": kind,
                "slug": path.stem,
                "title": title,
                "excerpt": body.strip().replace("\n", " ")[:160],
            })
            if len(hits) >= limit:
                return hits
    return hits


def _pick_uncompiled_raw(max_sources: int) -> list[Path]:
    manifest = _load_manifest()
    compiled = set(manifest.get("compiled_raw_ids") or [])
    pending: list[Path] = []
    for path in sorted(_raw_dir().glob("*.md"), key=lambda p: p.stat().st_mtime):
        text = path.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(text)
        raw_id = meta.get("id", path.stem)
        if raw_id not in compiled:
            pending.append(path)
    return pending[:max_sources]


def compile_wiki(*, max_sources: int = 3) -> dict[str, Any]:
    """Incrementally compile unprocessed raw sources into wiki articles."""
    _ensure_dirs()
    pending = _pick_uncompiled_raw(max_sources)
    if not pending:
        return {"ok": True, "compiled": 0, "articles_updated": [], "message": "No new raw sources to compile."}

    existing = list_articles(limit=50)
    existing_titles = [a["title"] for a in existing]
    articles_updated: list[str] = []
    manifest = _load_manifest()
    compiled_ids: list[str] = list(manifest.get("compiled_raw_ids") or [])

    for path in pending:
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        raw_id = meta.get("id", path.stem)
        title = meta.get("title", path.stem)

        prompt = (
            "You maintain a personal markdown wiki. Given a new source document, produce wiki updates.\n"
            "Reply with JSON only:\n"
            '{"articles":[{"slug":"kebab-case","title":"Concept Title","content":"markdown body with [[wikilinks]]","update_index_line":"- [[slug]] — one-line summary"}]}\n'
            f"Existing articles (avoid duplicates): {existing_titles[:30]}\n"
            f"Source title: {title}\n"
            f"Source URL: {meta.get('url', '')}\n\n"
            f"Source body:\n{body[:8000]}"
        )
        try:
            reply = provider_chat([{"role": "user", "content": prompt}], max_tokens=2000)
            data = _parse_json_object(str(reply))
        except Exception as exc:
            raise RuntimeError(f"compile failed for {title}: {exc}") from exc

        for article in data.get("articles") or []:
            slug = slugify(str(article.get("slug") or article.get("title") or "concept"))
            article_title = str(article.get("title") or slug.replace("-", " ").title())
            content = str(article.get("content") or "").strip()
            if not content:
                continue

            article_path = _articles_dir() / f"{slug}.md"
            if article_path.exists():
                _, existing_body = _parse_frontmatter(article_path.read_text(encoding="utf-8"))
                content = f"{existing_body.strip()}\n\n---\n\n{content}"

            article_path.write_text(
                _build_frontmatter({
                    "title": article_title,
                    "updated_at": _now_iso(),
                    "sources": title,
                })
                + content
                + "\n",
                encoding="utf-8",
            )
            articles_updated.append(slug)

            index_line = str(article.get("update_index_line") or f"- [[{slug}]] — {article_title}")
            _append_index_line(index_line)

        compiled_ids.append(raw_id)

    manifest["compiled_raw_ids"] = compiled_ids
    manifest["last_compile"] = _now_iso()
    _save_manifest(manifest)

    return {
        "ok": True,
        "compiled": len(pending),
        "articles_updated": articles_updated,
        "message": f"Compiled {len(pending)} source(s), updated {len(articles_updated)} article(s).",
    }


def health_check() -> dict[str, Any]:
    """LLM review of wiki index and articles — suggests gaps and inconsistencies."""
    _ensure_dirs()
    index = read_index()
    articles = list_articles(limit=30)
    summaries = "\n".join(f"- {a['title']}: {a['excerpt'][:100]}" for a in articles[:20])

    prompt = (
        "Review this personal wiki for health issues. Reply with JSON only:\n"
        '{"issues":[{"severity":"low|medium|high","message":"..."}],"suggestions":["question to explore"],"new_article_ideas":["title"]}\n'
        f"Index:\n{index[:3000]}\n\nArticle summaries:\n{summaries}"
    )
    reply = provider_chat([{"role": "user", "content": prompt}], max_tokens=1200)
    data = _parse_json_object(str(reply))

    manifest = _load_manifest()
    manifest["last_health_check"] = _now_iso()
    _save_manifest(manifest)

    return {
        "ok": True,
        "issues": data.get("issues") or [],
        "suggestions": data.get("suggestions") or [],
        "new_article_ideas": data.get("new_article_ideas") or [],
        "checked_at": manifest["last_health_check"],
    }


def wiki_status() -> dict[str, Any]:
    _ensure_dirs()
    manifest = _load_manifest()
    raw_count = len(list(_raw_dir().glob("*.md")))
    article_count = len(list(_articles_dir().glob("*.md")))
    uncompiled = len([r for r in list_raw(limit=500) if not r.get("compiled")])
    return {
        "raw_count": raw_count,
        "article_count": article_count,
        "uncompiled_count": uncompiled,
        "last_compile": manifest.get("last_compile"),
        "last_health_check": manifest.get("last_health_check"),
        "index_path": str(_index_path()),
        "wiki_dir": str(_wiki_dir()),
    }


def _gather_wiki_context(question: str, *, max_chars: int = 24000) -> tuple[str, list[str]]:
    """Assemble index + relevant articles/raw for Q&A."""
    parts: list[str] = []
    sources: list[str] = []

    index = read_index()
    if index.strip():
        parts.append(f"## Wiki index\n{index[:5000]}")

    hits = search_wiki(question, limit=10)
    seen: set[str] = set()

    for hit in hits:
        key = f"{hit['type']}:{hit['slug']}"
        if key in seen:
            continue
        seen.add(key)

        if hit["type"] == "article":
            article = get_article(hit["slug"])
            if not article:
                continue
            parts.append(f"## Article: {article['title']}\n{article['content'][:8000]}")
            sources.append(article["title"])
        else:
            raw = get_raw(hit["slug"])
            if not raw:
                continue
            parts.append(f"## Raw source: {raw['title']}\n{raw['content'][:6000]}")
            sources.append(raw["title"])

    if not hits:
        for summary in list_articles(limit=6):
            article = get_article(summary["slug"])
            if not article:
                continue
            parts.append(f"## Article: {article['title']}\n{article['content'][:4000]}")
            sources.append(article["title"])

    context = "\n\n".join(parts)[:max_chars]
    return context, sources


def ask_wiki(question: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Answer a question using compiled wiki articles and raw sources as context."""
    question = question.strip()
    if not question:
        raise ValueError("question is required")

    if not list_articles(limit=1) and not list_raw(limit=1):
        return {
            "reply": "Wiki is empty. Save a page, tap + Wiki, then Compile.",
            "sources": [],
        }

    context, sources = _gather_wiki_context(question)

    system = (
        "Answer from the user's wiki only. Cite article titles. "
        "Say what's missing if context is thin."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for turn in (history or [])[-8:]:
        role = str(turn.get("role", "")).strip()
        content = str(turn.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({
        "role": "user",
        "content": f"Wiki context:\n{context}\n\nQuestion: {question}",
    })
    reply = provider_chat(messages, max_tokens=1800)
    return {"reply": str(reply).strip(), "sources": list(dict.fromkeys(sources))}


def _append_index_line(line: str) -> None:
    index = read_index()
    if line.strip() in index:
        return
    if "## Articles" not in index:
        index = index.rstrip() + "\n\n## Articles\n\n"
    index = index.rstrip() + f"\n{line.strip()}\n"
    _index_path().write_text(index, encoding="utf-8")


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("LLM response did not contain JSON object")
    return json.loads(text[start : end + 1])
