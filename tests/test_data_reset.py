"""Tests for data reset endpoints."""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def backend_url(tmp_path, monkeypatch):
    port = __import__("socket").socket()
    port.bind(("127.0.0.1", 0))
    free_port = port.getsockname()[1]
    port.close()

    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    monkeypatch.setenv("KB_PORT", str(free_port))

    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.frontend_backend as fb
    reload(fb)

    from http.server import HTTPServer
    import threading

    server = HTTPServer(("127.0.0.1", free_port), fb.FrontendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{free_port}", tmp_path
    server.shutdown()


def _post(url: str, path: str) -> tuple[int, dict]:
    import urllib.request
    req = urllib.request.Request(
        f"{url}{path}",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def test_library_clear_only_removes_library(backend_url):
    url, kb_root = backend_url
    lib_dir = kb_root / "library"
    lib_dir.mkdir(parents=True)
    (lib_dir / "saved_pages.json").write_text("[]")
    events_dir = kb_root / "events" / "clean"
    events_dir.mkdir(parents=True)
    (events_dir / "day.jsonl").write_text('{"id":"e1"}\n')

    status, body = _post(url, "/library/clear")
    assert status == 200
    assert body["scope"] == "library"
    assert not lib_dir.exists()
    assert (events_dir / "day.jsonl").exists()


def test_delete_all_wipes_runtime_data(backend_url):
    url, kb_root = backend_url
    for rel in [
        "library/saved_pages.json",
        "events/clean/day.jsonl",
        "relationships/profiles.json",
        "auth/gcal.json",
        "buckets/classifications.json",
    ]:
        path = kb_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")

    status, body = _post(url, "/delete-all")
    assert status == 200
    assert body["scope"] == "all"
    assert not (kb_root / "library" / "saved_pages.json").exists()
    assert not (kb_root / "events" / "clean" / "day.jsonl").exists()
    assert not (kb_root / "relationships" / "profiles.json").exists()
    assert not (kb_root / "auth" / "gcal.json").exists()
    assert not (kb_root / "buckets" / "classifications.json").exists()
