"""HTTP integration tests for Chrome extension backend endpoints."""
from __future__ import annotations

import json
import socket
import threading
from http.server import HTTPServer
from urllib import error, request

import pytest


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def backend_url(tmp_path, monkeypatch):
    port = _free_port()
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    monkeypatch.setenv("KB_PORT", str(port))

    from importlib import reload
    import core.config as cfg_mod
    reload(cfg_mod)
    import core.page_context_service as pcs
    import core.library_service as lib
    import core.frontend_backend as fb
    reload(pcs)
    reload(lib)
    reload(fb)

    server = HTTPServer(("127.0.0.1", port), fb.FrontendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}


def test_health_endpoint(backend_url):
    status, body = _request("GET", f"{backend_url}/health")
    assert status == 200
    assert body["ok"] is True
    assert body["api_version"] == 2
    assert "llm_provider" in body
    assert body["api_version"] == 2


def test_options_returns_cors_headers(backend_url):
    req = request.Request(f"{backend_url}/health", method="OPTIONS")
    with request.urlopen(req, timeout=10) as resp:
        assert resp.status == 204
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"


def test_page_context_and_history(backend_url):
    status, body = _request("POST", f"{backend_url}/page-context", {
        "url": "https://example.com/article",
        "title": "Example Article",
        "site": "example.com",
        "headings": ["Intro"],
        "paragraphs": ["A paragraph about transformers."],
        "visible_text": "Example visible text",
        "page_type": "article",
    })
    assert status == 200
    page_id = body["page"]["id"]
    assert page_id

    status, history = _request("GET", f"{backend_url}/history?limit=5")
    assert status == 200
    assert history["history"][0]["id"] == page_id


def test_ask_endpoint(backend_url, monkeypatch):
    import core.retrieval.page_chat as page_chat_mod
    monkeypatch.setattr(
        page_chat_mod,
        "provider_chat",
        lambda messages, stream=False: "This page discusses scaling laws.",
    )

    status, body = _request("POST", f"{backend_url}/ask", {
        "question": "What is this about?",
        "page": {
            "url": "https://example.com/paper",
            "title": "Paper",
            "visible_text": "Scaling laws for language models.",
        },
        "stream": False,
    })
    assert status == 200
    assert "scaling laws" in body["reply"].lower()


def test_library_save_and_list(backend_url, monkeypatch):
    import core.library_service as lib
    monkeypatch.setattr(lib, "_generate_summary", lambda page: "Summary line")
    monkeypatch.setattr(lib, "ingest_text", lambda **kwargs: {"id": "e1"})

    status, body = _request("POST", f"{backend_url}/library/save-page", {
        "page": {
            "url": "https://example.com/lib",
            "title": "Library Page",
            "visible_text": "Some content",
        },
    })
    assert status == 200
    page_id = body["page"]["id"]

    status, listed = _request("GET", f"{backend_url}/library/pages")
    assert status == 200
    assert listed["pages"][0]["id"] == page_id

    status, detail = _request("GET", f"{backend_url}/library/pages/{page_id}")
    assert status == 200
    assert detail["page"]["title"] == "Library Page"


def test_library_quotes(backend_url, monkeypatch):
    import core.library_service as lib
    monkeypatch.setattr(lib, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(lib, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(lib, "remember_concept", lambda **kwargs: {"id": "c1"})

    status, saved = _request("POST", f"{backend_url}/library/save-page", {
        "page": {"url": "https://example.com/q", "title": "Q Page", "visible_text": "x"},
    })
    page_id = saved["page"]["id"]

    status, body = _request("POST", f"{backend_url}/library/quotes", {
        "text": "A memorable quote",
        "page_id": page_id,
        "page_url": "https://example.com/q",
        "page_title": "Q Page",
    })
    assert status == 200
    assert body["quote"]["text"] == "A memorable quote"


def test_library_quotes_by_url(backend_url, monkeypatch):
    import core.library_service as lib
    monkeypatch.setattr(lib, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(lib, "ingest_text", lambda **kwargs: {"id": "e1"})
    monkeypatch.setattr(lib, "remember_concept", lambda **kwargs: {"id": "c1"})

    _request("POST", f"{backend_url}/library/quotes", {
        "text": "Orphan quote",
        "page_url": "https://example.com/orphan",
        "page_title": "Orphan Page",
    })
    status, body = _request("GET", f"{backend_url}/library/quotes?page_url=https://example.com/orphan")
    assert status == 200
    assert body["quotes"][0]["text"] == "Orphan quote"


def test_library_clear(backend_url, monkeypatch):
    import core.library_service as lib
    monkeypatch.setattr(lib, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(lib, "ingest_text", lambda **kwargs: {"id": "e1"})

    _request("POST", f"{backend_url}/library/save-page", {
        "page": {"url": "https://example.com/clear", "title": "Clear", "visible_text": "x"},
    })
    status, body = _request("POST", f"{backend_url}/library/clear")
    assert status == 200
    assert body["ok"] is True
    assert body.get("scope") == "library"

    status, listed = _request("GET", f"{backend_url}/library/pages")
    assert status == 200
    assert listed["pages"] == []


def test_remember_endpoint(backend_url, monkeypatch):
    status, saved = _request("POST", f"{backend_url}/page-context", {
        "url": "https://example.com/note",
        "title": "Note",
        "visible_text": "Some content",
    })
    page_id = saved["page"]["id"]

    import core.page_context_service as pcs
    monkeypatch.setattr(pcs, "ingest_text", lambda **kwargs: {"id": "event-123"})
    monkeypatch.setattr(pcs, "remember_concept", lambda **kwargs: {
        "id": "concept:test", "name": "Test", "understanding_score": 0.4, "related_names": [],
    })

    status, body = _request("POST", f"{backend_url}/remember", {
        "page_id": page_id,
        "selected_text": "important passage",
        "note": "remember this",
    })
    assert status == 200
    assert body["ok"] is True


def test_search_requires_query(backend_url):
    status, body = _request("GET", f"{backend_url}/search")
    assert status == 400
    assert "q is required" in body["error"]


def test_concepts_endpoint(backend_url, monkeypatch):
    import core.frontend_backend as fb
    monkeypatch.setattr(fb, "list_concepts", lambda limit=50, query="": [{"id": "concept:test", "name": "Test"}])

    status, body = _request("GET", f"{backend_url}/concepts")
    assert status == 200
    assert body["concepts"][0]["name"] == "Test"


def test_connections_endpoint(backend_url, monkeypatch):
    import core.frontend_backend as fb
    monkeypatch.setattr(fb, "get_connections", lambda url="", query="", top_k=5: [])

    status, body = _request("GET", f"{backend_url}/connections?url=https://example.com")
    assert status == 200
    assert body["connections"] == []


def test_buckets_taxonomy(backend_url):
    status, body = _request("GET", f"{backend_url}/buckets/taxonomy")
    assert status == 200
    assert "leaves" in body
    assert "tree" in body
    assert "Work/Deep Work" in body["leaves"]


def test_buckets_recent(backend_url):
    status, body = _request("GET", f"{backend_url}/buckets/recent?days=7&limit=10")
    assert status == 200
    assert "events" in body
    assert isinstance(body["events"], list)


def test_buckets_override(backend_url, tmp_path, monkeypatch):
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload
    import core.config as cfg_mod
    import core.memory.buckets_service as bs_mod
    reload(cfg_mod)
    reload(bs_mod)
    cfg_mod.config.ensure_dirs()

    status, body = _request("POST", f"{backend_url}/buckets/override", {
        "event_id": "evt-test",
        "bucket": "Work/Meetings",
    })
    assert status == 200
    assert body["ok"] is True
    assert body["bucket"] == "Work/Meetings"


def test_dashboard_time(backend_url):
    status, body = _request("GET", f"{backend_url}/dashboard/time?days=7")
    assert status == 200
    assert body["days"] == 7
    assert "breakdown" in body


def test_relationships_list(backend_url):
    status, body = _request("GET", f"{backend_url}/relationships")
    assert status == 200
    assert "profiles" in body


def test_proactive_insights(backend_url, monkeypatch):
    import core.proactive.engine as engine
    monkeypatch.setattr(
        engine,
        "get_insights",
        lambda max_insights=5: [{"type": "email", "title": "Test", "body": "Body", "urgency": 2}],
    )

    status, body = _request("GET", f"{backend_url}/proactive")
    assert status == 200
    assert body["insights"][0]["title"] == "Test"


def test_settings_endpoint(backend_url):
    status, body = _request("GET", f"{backend_url}/settings")
    assert status == 200
    assert "proactive_interval_minutes" in body
    assert body["proactive_interval_minutes"] >= 5
    assert "env_path" in body
    assert "llm_provider" in body
    assert "setup_notes" in body


def test_settings_update_endpoint(backend_url, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("KB_LLM_PROVIDER=auto\nOPENAI_API_KEY=\n", encoding="utf-8")
    monkeypatch.setattr("core.env_settings._ENV_PATH", env_file)

    status, body = _request("POST", f"{backend_url}/settings", {
        "llm_provider": "openai",
        "openai_api_key": "sk-test-key-1234",
        "openai_model": "gpt-4o-mini",
    })
    assert status == 200
    assert body["settings"]["llm_provider_setting"] == "openai"
    assert body["settings"]["openai_configured"] is True

    status, loaded = _request("GET", f"{backend_url}/settings")
    assert status == 200
    assert loaded["openai_configured"] is True


def test_imessage_status(backend_url):
    status, body = _request("GET", f"{backend_url}/integrations/imessage/status")
    assert status == 200
    assert "available" in body


def test_update_page_title_patch(backend_url, monkeypatch):
    import core.library_service as lib
    monkeypatch.setattr(lib, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(lib, "ingest_text", lambda **kwargs: {"id": "e1"})

    status, saved = _request("POST", f"{backend_url}/library/save-page", {
        "page": {"url": "https://example.com/title-edit", "title": "Before", "visible_text": "x"},
    })
    assert status == 200
    page_id = saved["page"]["id"]

    status, body = _request("PATCH", f"{backend_url}/library/pages/{page_id}", {
        "title": "After edit",
    })
    assert status == 200
    assert body["page"]["title"] == "After edit"


def test_update_page_metadata_patch(backend_url, monkeypatch):
    import core.library_service as lib
    monkeypatch.setattr(lib, "_generate_summary", lambda page: "Summary")
    monkeypatch.setattr(lib, "ingest_text", lambda **kwargs: {"id": "e1"})

    status, saved = _request("POST", f"{backend_url}/library/save-page", {
        "page": {"url": "https://example.com/meta-edit", "title": "Before", "visible_text": "x"},
    })
    assert status == 200
    page_id = saved["page"]["id"]

    status, body = _request("PATCH", f"{backend_url}/library/pages/{page_id}", {
        "metadata": {
            "author": "Author Name",
            "date": "2024",
            "custom": [{"key": "Source", "value": "Web"}],
        },
    })
    assert status == 200
    assert body["page"]["metadata"]["author"] == "Author Name"


def test_quote_patch_and_delete(backend_url, monkeypatch):
    import core.library_service as lib
    monkeypatch.setattr(lib, "ingest_text", lambda **kwargs: {"id": "e1"})

    status, created = _request("POST", f"{backend_url}/library/quotes", {
        "text": "Original quote",
        "page_url": "https://example.com/quote-edit",
        "page_title": "Page",
    })
    assert status == 200
    quote_id = created["quote"]["id"]

    status, body = _request("PATCH", f"{backend_url}/library/quotes/{quote_id}", {
        "text": "Updated quote",
        "note": "My note",
    })
    assert status == 200
    assert body["quote"]["text"] == "Updated quote"

    status, _ = _request("DELETE", f"{backend_url}/library/quotes/{quote_id}")
    assert status == 200
