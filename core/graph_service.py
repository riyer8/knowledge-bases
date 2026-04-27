from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any


def graph_dependencies_path(root: Path) -> Path:
    return root / "inputs" / ".graph-dependencies.json"


def load_manual_dependencies(root: Path) -> list[dict[str, str]]:
    path = graph_dependencies_path(root)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source", "")).strip()
        target = str(item.get("target", "")).strip()
        if source and target and source != target:
            rows.append({"source": source, "target": target})
    return rows


def save_manual_dependencies(root: Path, dependencies: list[dict[str, str]]) -> None:
    path = graph_dependencies_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dependencies, ensure_ascii=True, indent=2), encoding="utf-8")


def add_manual_dependency(root: Path, source: str, target: str) -> dict[str, str]:
    source = source.strip()
    target = target.strip()
    if not source or not target or source == target:
        raise ValueError("Dependency requires different non-empty source and target.")
    dependencies = load_manual_dependencies(root)
    if not any(dep["source"] == source and dep["target"] == target for dep in dependencies):
        dependencies.append({"source": source, "target": target})
        dependencies.sort(key=lambda dep: (dep["source"], dep["target"]))
        save_manual_dependencies(root, dependencies)
    return {"source": source, "target": target}


def build_markdown_graph(
    root: Path,
    *,
    only_orphans: bool = False,
    only_unlinked: bool = False,
    folder_prefix: str | None = None,
) -> dict[str, Any]:
    markdown_files = sorted(root.rglob("*.md"))
    nodes: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []
    known_by_stem: dict[str, str] = {}

    for file_path in markdown_files:
        rel = str(file_path.relative_to(root))
        stem = file_path.stem.lower()
        folder = str(Path(rel).parent)
        if folder == ".":
            folder = "(root)"
        nodes.append({"id": rel, "label": file_path.name, "path": rel, "folder": folder})
        known_by_stem[stem] = rel
    known_ids = {node["id"] for node in nodes}

    wikilink_pattern = re.compile(r"\[\[([^\]|#]+)")
    md_link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for file_path in markdown_files:
        source_id = str(file_path.relative_to(root))
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        targets: set[str] = set()
        for name in wikilink_pattern.findall(content):
            key = name.strip().split("/")[-1].lower()
            if key in known_by_stem:
                targets.add(known_by_stem[key])

        for link in md_link_pattern.findall(content):
            clean = link.strip()
            if clean.startswith("http://") or clean.startswith("https://"):
                continue
            clean = clean.split("#")[0]
            if not clean:
                continue
            if clean.endswith(".md"):
                target = str((file_path.parent / clean).resolve())
                try:
                    target_rel = str(Path(target).relative_to(root.resolve()))
                    if target_rel in known_ids:
                        targets.add(target_rel)
                except Exception:
                    pass
            else:
                key = Path(clean).stem.lower()
                if key in known_by_stem:
                    targets.add(known_by_stem[key])

        for target_id in sorted(targets):
            if target_id != source_id:
                edges.append({"source": source_id, "target": target_id})

    incoming_count: dict[str, int] = {node["id"]: 0 for node in nodes}
    outgoing_count: dict[str, int] = {node["id"]: 0 for node in nodes}
    manual_dependencies = load_manual_dependencies(root)
    for dependency in manual_dependencies:
        src = dependency["source"]
        dst = dependency["target"]
        if src in known_ids and dst in known_ids and src != dst:
            edges.append({"source": src, "target": dst})

    for edge in edges:
        outgoing_count[edge["source"]] = outgoing_count.get(edge["source"], 0) + 1
        incoming_count[edge["target"]] = incoming_count.get(edge["target"], 0) + 1

    enriched_nodes: list[dict[str, Any]] = []
    for node in nodes:
        node_id = node["id"]
        out = outgoing_count.get(node_id, 0)
        inc = incoming_count.get(node_id, 0)
        enriched = {
            **node,
            "outgoing": out,
            "incoming": inc,
            "degree": out + inc,
            "isOrphan": out + inc == 0,
            "isUnlinked": out == 0,
        }
        enriched_nodes.append(enriched)

    if folder_prefix:
        enriched_nodes = [n for n in enriched_nodes if n["folder"].startswith(folder_prefix)]
    if only_orphans:
        enriched_nodes = [n for n in enriched_nodes if n["isOrphan"]]
    if only_unlinked:
        enriched_nodes = [n for n in enriched_nodes if n["isUnlinked"]]

    allowed_ids = {node["id"] for node in enriched_nodes}
    filtered_edges = [
        edge for edge in edges if edge["source"] in allowed_ids and edge["target"] in allowed_ids
    ]

    folders = sorted({node["folder"] for node in nodes})
    return {
        "nodes": enriched_nodes,
        "edges": filtered_edges,
        "manualDependencies": [d for d in manual_dependencies if d["source"] in known_ids and d["target"] in known_ids],
        "root": str(root),
        "folders": folders,
    }
