from __future__ import annotations

import json
from pathlib import Path

from core.config import config

# Graph is stored as adjacency: { node_id: { neighbor_id: { weight, edge_type } } }


def _graph_path() -> Path:
    return config.graph_dir / "edges.json"


def load_graph() -> dict:
    path = _graph_path()
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_graph(graph: dict) -> None:
    config.graph_dir.mkdir(parents=True, exist_ok=True)
    _graph_path().write_text(json.dumps(graph, indent=2))


def add_edge(from_node: str, to_node: str, edge_type: str, weight: float = 1.0) -> None:
    """Add or strengthen an edge between two nodes."""
    graph = load_graph()
    graph.setdefault(from_node, {})
    existing = graph[from_node].get(to_node, {})
    graph[from_node][to_node] = {
        "edge_type": edge_type,
        "weight": round(existing.get("weight", 0.0) + weight, 4),
    }
    _save_graph(graph)


def get_neighbors(node_id: str, min_weight: float = 0.0) -> list[dict]:
    """Return all neighbors of a node with their edge metadata."""
    graph = load_graph()
    neighbors = graph.get(node_id, {})
    return [
        {"node": neighbor, **meta}
        for neighbor, meta in neighbors.items()
        if meta.get("weight", 0) >= min_weight
    ]


def index_event(event: dict) -> None:
    """
    Extract graph edges from a clean event and add them to the graph.
    Edges are created between:
    - event_id ↔ each person hash (co-occurrence)
    - event_id ↔ bucket (classification)
    - person hash ↔ source (relationship context)
    """
    event_id = event.get("id", "")
    source = event.get("source", "unknown")
    entities = event.get("entities", [])
    bucket = event.get("bucket")  # set by bucket_classifier if available

    for entity in entities:
        if entity.get("type") == "PERSON":
            person_hash = entity.get("hash", "")
            if person_hash:
                add_edge(event_id, f"person:{person_hash}", edge_type="mentions", weight=1.0)
                add_edge(f"person:{person_hash}", f"source:{source}", edge_type="seen_in", weight=0.5)

    if bucket:
        add_edge(event_id, f"bucket:{bucket}", edge_type="classified_as", weight=1.0)


def get_person_events(person_hash: str) -> list[str]:
    """Return event IDs that mention a given person hash."""
    node_id = f"person:{person_hash}"
    graph = load_graph()
    event_ids: list[str] = []
    for node, neighbors in graph.items():
        if node_id in neighbors and not node.startswith("person:") and not node.startswith("bucket:"):
            event_ids.append(node)
    return event_ids
