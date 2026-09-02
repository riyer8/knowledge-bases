from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from core.ingestion.pipeline import ingest_text
from core.memory.graph import load_graph


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_graph_response(
    only_orphans: bool = False,
    only_unlinked: bool = False,
    folder_filter: str | None = None,
) -> dict:
    adjacency = load_graph()

    all_node_ids: set[str] = set(adjacency.keys())
    for neighbors in adjacency.values():
        all_node_ids.update(neighbors.keys())

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


def load_manual_entries() -> list[dict]:
    from core.config import config

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


def manual_entry_meta(kind: str, value: str) -> dict:
    if kind == "text":
        return {"kind": "text", "value": value, "text": value}
    if kind == "url":
        return {"kind": "url", "value": value, "url": value}
    return {"kind": "file", "value": value, "source_path": value}


def ingest_manual(kind: str, value: str, created_at: str) -> tuple[str, str]:
    meta = manual_entry_meta(kind, value)

    if kind == "file":
        source_path = Path(value)
        if not source_path.exists() or not source_path.is_file():
            raise ValueError(f"File not found: {value}")
        text = source_path.read_text(encoding="utf-8", errors="ignore")
        meta["source_path"] = str(source_path)
    elif kind == "url":
        text = value
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


def demo_hint(prompt: str) -> str | None:
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


def delete_all_data() -> None:
    from core.config import config

    for subdir in [
        config.kb_root / "library",
        config.events_raw_dir,
        config.events_clean_dir,
        config.index_dir,
        config.graph_dir,
        config.hashes_dir,
        config.buckets_dir,
        config.pages_dir,
        config.auth_dir,
        config.kb_root / "wiki",
        config.kb_root / "relationships",
    ]:
        if subdir.exists():
            shutil.rmtree(subdir)
    if config.paused_log.exists():
        config.paused_log.unlink()
    config.ensure_dirs()
