#!/usr/bin/env python3
"""Local backend for manual input ingestion."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_ROOT))
from screenshot.screenshot_service import capture_screenshot


def default_manual_root() -> Path:
    return Path(__file__).resolve().parent


MANUAL_ROOT = Path(os.getenv("KB_MANUAL_INPUT_ROOT", default_manual_root()))
UPLOADS_ROOT = MANUAL_ROOT / "uploads"
FILES_DIR = UPLOADS_ROOT / "files"
TEXT_DIR = UPLOADS_ROOT / "text"
URL_DIR = UPLOADS_ROOT / "urls"
LOG_PATH = MANUAL_ROOT / "entries.jsonl"
GRAPH_ROOT = Path(os.getenv("KB_GRAPH_ROOT", Path(__file__).resolve().parents[2]))
SCREENSHOT_ROOT = Path(
    os.getenv("KB_SCREENSHOT_ROOT", Path(__file__).resolve().parents[1] / "screenshot" / "captures")
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    URL_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    if not cleaned:
        cleaned = "entry"
    return cleaned[:max_length]


def write_markdown(dir_path: Path, title: str, body: str) -> Path:
    ensure_dirs()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = f"{timestamp}-{slugify(title)}"
    candidate = dir_path / f"{base}.md"
    counter = 1
    while candidate.exists():
        candidate = dir_path / f"{base}-{counter}.md"
        counter += 1
    candidate.write_text(body, encoding="utf-8")
    return candidate


def unique_destination(path: Path) -> Path:
    candidate = FILES_DIR / path.name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        next_candidate = FILES_DIR / f"{stem}-{counter}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        counter += 1


def append_entry(entry: dict[str, Any]) -> None:
    ensure_dirs()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")


def load_entries() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows.reverse()
    return rows


def build_chat_reply(prompt: str) -> str:
    entries = load_entries()
    recent = entries[:5]
    if not recent:
        return (
            "I received your message, but there are no manual inputs yet. "
            "Add files, URLs, or text in the Manual Inputs tab first."
        )

    lines = []
    for idx, item in enumerate(recent, start=1):
        kind = item.get("kind", "unknown")
        value = str(item.get("value", ""))
        lines.append(f"{idx}. [{kind}] {value}")

    context = "\n".join(lines)
    return (
        f"You said: {prompt}\n\n"
        f"I found {len(recent)} recent manual input(s):\n{context}\n\n"
        "This is the full frontend-backend cycle response from Python."
    )


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
        "root": str(root),
        "folders": folders,
    }


class ManualInputHandler(BaseHTTPRequestHandler):
    server_version = "ManualInputServer/1.0"

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path not in {"/manual-input", "/chat", "/screenshot"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload_raw = self.rfile.read(content_length)
            payload = json.loads(payload_raw.decode("utf-8"))
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"})
            return

        if self.path == "/chat":
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Payload must include prompt"})
                return
            self._send_json(HTTPStatus.OK, {"reply": build_chat_reply(prompt)})
            return

        if self.path == "/screenshot":
            try:
                shot = capture_screenshot(SCREENSHOT_ROOT)
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Screenshot failed: {exc}"})
                return
            self._send_json(HTTPStatus.OK, {"ok": True, "screenshot": shot})
            return

        kind = str(payload.get("kind", "")).strip().lower()
        value = str(payload.get("value", "")).strip()
        created_at = str(payload.get("createdAt", "")).strip() or now_iso()

        if kind not in {"file", "url", "text"} or not value:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Payload must include valid kind and value"})
            return

        entry: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "kind": kind,
            "receivedAt": now_iso(),
            "createdAt": created_at,
        }

        try:
            if kind == "file":
                source_path = Path(value)
                if not source_path.exists() or not source_path.is_file():
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "File path does not exist"})
                    return

                ensure_dirs()
                destination = unique_destination(source_path)
                shutil.copy2(source_path, destination)
                entry["value"] = str(destination.relative_to(MANUAL_ROOT))
                entry["sourcePath"] = str(source_path)
            elif kind == "text":
                md_path = write_markdown(
                    TEXT_DIR,
                    title="manual-text",
                    body=value,
                )
                entry["value"] = str(md_path.relative_to(MANUAL_ROOT))
                entry["text"] = value
            elif kind == "url":
                md_path = write_markdown(
                    URL_DIR,
                    title=value,
                    body=f"# Saved URL\n\n{value}\n",
                )
                entry["value"] = str(md_path.relative_to(MANUAL_ROOT))
                entry["url"] = value
            else:
                entry["value"] = value

            append_entry(entry)
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Failed to process input: {exc}"})
            return

        self._send_json(HTTPStatus.OK, {"ok": True, "entry": entry})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "manualRoot": str(MANUAL_ROOT),
                    "time": now_iso(),
                },
            )
            return

        if path == "/manual-inputs":
            self._send_json(HTTPStatus.OK, load_entries())
            return

        if path == "/graph":
            only_orphans = query.get("orphans", ["0"])[0] == "1"
            only_unlinked = query.get("unlinked", ["0"])[0] == "1"
            folder = query.get("folder", [""])[0].strip() or None
            self._send_json(
                HTTPStatus.OK,
                build_markdown_graph(
                    GRAPH_ROOT,
                    only_orphans=only_orphans,
                    only_unlinked=only_unlinked,
                    folder_prefix=folder,
                ),
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    ensure_dirs()
    server = HTTPServer(("127.0.0.1", 8765), ManualInputHandler)
    print("Manual input backend listening on http://127.0.0.1:8765")
    print(f"Writing to: {MANUAL_ROOT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
