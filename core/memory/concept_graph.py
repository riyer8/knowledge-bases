from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from core.config import config
from core.memory.graph import add_edge

_CONCEPT_PREFIX = "concept:"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _concepts_path():
    return config.graph_dir / "concepts.json"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or str(uuid.uuid4())[:8]


def _load_concepts() -> dict[str, dict[str, Any]]:
    path = _concepts_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_concepts(concepts: dict[str, dict[str, Any]]) -> None:
    config.graph_dir.mkdir(parents=True, exist_ok=True)
    _concepts_path().write_text(json.dumps(concepts, indent=2), encoding="utf-8")


def _concept_id(slug: str) -> str:
    return f"{_CONCEPT_PREFIX}{slug}"


def get_concept(concept_id: str) -> dict[str, Any] | None:
    return _load_concepts().get(concept_id)


def list_concepts(limit: int = 50, query: str = "") -> list[dict[str, Any]]:
    concepts = list(_load_concepts().values())
    concepts.sort(key=lambda c: c.get("last_encountered", ""), reverse=True)
    if query:
        needle = query.lower()
        concepts = [
            c for c in concepts
            if needle in c.get("name", "").lower()
            or any(needle in n.lower() for n in c.get("related_names", []))
        ]
    return concepts[: max(1, min(limit, 200))]


def _extract_concept_metadata(passage: str, page_title: str = "", note: str = "") -> dict[str, Any]:
    """Derive concept name and related topics from a passage."""
    passage = passage.strip()
    if not passage:
        return {"name": "Untitled concept", "related": []}

    try:
        from core.llm_providers import chat as provider_chat

        prompt = (
            "Extract the main concept from this reading passage. "
            "Reply with JSON only, no markdown:\n"
            '{"concept": "short concept name", "related": ["topic1", "topic2"]}\n\n'
            f"Page: {page_title}\n"
            f"Passage: {passage[:1200]}\n"
        )
        if note.strip():
            prompt += f"User note: {note.strip()}\n"
        raw = str(provider_chat([{"role": "user", "content": prompt}], stream=False)).strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end + 1])
            name = str(parsed.get("concept", "")).strip()
            related = [str(r).strip() for r in parsed.get("related", []) if str(r).strip()]
            if name:
                return {"name": name[:120], "related": related[:8]}
    except Exception:
        pass

    # Heuristic fallback: first sentence or first ~6 words
    sentence = passage.split(".")[0].strip() or passage
    words = sentence.split()[:6]
    name = " ".join(words)
    if len(name) > 60:
        name = " ".join(words[:4]) + "…"
    return {"name": name[:120], "related": []}


def remember_concept(
    *,
    passage: str,
    page_id: str,
    page_title: str,
    page_url: str,
    note: str = "",
    event_id: str = "",
) -> dict[str, Any]:
    """Create or update a concept node from a remembered passage."""
    meta = _extract_concept_metadata(passage, page_title=page_title, note=note)
    slug = _slugify(meta["name"])
    concept_id = _concept_id(slug)
    concepts = _load_concepts()
    now = _now_iso()

    source = {
        "page_id": page_id,
        "url": page_url,
        "title": page_title,
        "passage": passage[:2000],
        "event_id": event_id,
        "at": now,
    }

    if concept_id in concepts:
        concept = concepts[concept_id]
        concept["times_referenced"] = int(concept.get("times_referenced", 0)) + 1
        concept["last_encountered"] = now
        concept["understanding_score"] = min(
            1.0, round(float(concept.get("understanding_score", 0.3)) + 0.08, 2)
        )
        sources = concept.get("sources", [])
        sources.insert(0, source)
        concept["sources"] = sources[:20]
        if note.strip():
            notes = concept.get("notes", [])
            if note.strip() not in notes:
                notes.insert(0, note.strip())
            concept["notes"] = notes[:10]
    else:
        concept = {
            "id": concept_id,
            "name": meta["name"],
            "slug": slug,
            "sources": [source],
            "first_encountered": now,
            "last_encountered": now,
            "times_referenced": 1,
            "related": [],
            "related_names": meta.get("related", []),
            "notes": [note.strip()] if note.strip() else [],
            "understanding_score": 0.35,
        }

    # Link related concepts
    related_ids: list[str] = []
    for related_name in meta.get("related", []):
        related_slug = _slugify(related_name)
        related_id = _concept_id(related_slug)
        related_ids.append(related_id)
        if related_id not in concepts:
            concepts[related_id] = {
                "id": related_id,
                "name": related_name,
                "slug": related_slug,
                "sources": [],
                "first_encountered": now,
                "last_encountered": now,
                "times_referenced": 0,
                "related": [concept_id],
                "related_names": [],
                "notes": [],
                "understanding_score": 0.2,
            }
        else:
            rel = concepts[related_id]
            links = rel.get("related", [])
            if concept_id not in links:
                links.append(concept_id)
            rel["related"] = links[:20]

        add_edge(concept_id, related_id, edge_type="related_to", weight=1.0)
        add_edge(related_id, concept_id, edge_type="related_to", weight=1.0)

    concept["related"] = list(dict.fromkeys((concept.get("related", []) + related_ids)))[:20]
    add_edge(concept_id, f"page:{page_id}", edge_type="learned_from", weight=1.0)
    if event_id:
        add_edge(concept_id, event_id, edge_type="source_event", weight=1.0)

    concepts[concept_id] = concept
    _save_concepts(concepts)
    return concept


def related_for_page(page_url: str = "", query: str = "", limit: int = 8) -> list[dict[str, Any]]:
    """Return concepts related to a page URL or search query."""
    concepts = list(_load_concepts().values())
    if not concepts:
        return []

    needle = (query or page_url).lower().strip()
    scored: list[tuple[float, dict[str, Any]]] = []
    for concept in concepts:
        score = 0.0
        name = concept.get("name", "").lower()
        if needle and needle in name:
            score += 3.0
        for source in concept.get("sources", []):
            if page_url and source.get("url") == page_url:
                score += 5.0
            if needle and needle in str(source.get("title", "")).lower():
                score += 2.0
            if needle and needle in str(source.get("passage", "")).lower():
                score += 1.0
        score += float(concept.get("times_referenced", 0)) * 0.1
        if score > 0:
            scored.append((score, concept))

    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored and not needle:
        concepts.sort(key=lambda c: c.get("last_encountered", ""), reverse=True)
        return concepts[:limit]
    return [c for _, c in scored[:limit]]


def bump_understanding_from_question(concept_names: list[str], delta: float = 0.05) -> None:
    """Slightly increase understanding when user engages with concepts."""
    concepts = _load_concepts()
    changed = False
    for concept in concepts.values():
        if concept.get("name") in concept_names:
            concept["understanding_score"] = min(
                1.0, round(float(concept.get("understanding_score", 0.3)) + delta, 2)
            )
            changed = True
    if changed:
        _save_concepts(concepts)
