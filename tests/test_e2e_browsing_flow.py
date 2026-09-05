"""End-to-end browsing flow — mirrors Chrome extension side panel usage."""
from __future__ import annotations

import json
from urllib import request

import pytest

from tests.test_extension_api import _request, backend_url


def _request_sse_post(url: str, payload: dict) -> str:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    tokens: list[str] = []
    with request.urlopen(req, timeout=30) as resp:
        assert "text/event-stream" in (resp.headers.get("Content-Type") or "")
        while True:
            raw = resp.readline()
            if not raw:
                break
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            chunk = json.loads(line[5:].strip())
            if chunk.get("error"):
                raise AssertionError(chunk["error"])
            if chunk.get("done"):
                break
            if chunk.get("token"):
                tokens.append(chunk["token"])
    return "".join(tokens)


def _sample_page(
    *,
    url: str,
    title: str,
    selected: str = "",
) -> dict:
    return {
        "url": url,
        "title": title,
        "site": url.split("/")[2] if "://" in url else "example.com",
        "headings": ["Introduction", "Key ideas"],
        "paragraphs": [
            "Transformers use self-attention to model long-range dependencies in text.",
            "Scaling laws predict performance improves with compute and data.",
        ],
        "code_blocks": [],
        "links": [{"text": "Attention paper", "href": "https://example.com/attention"}],
        "selected_text": selected,
        "page_type": "article",
        "visible_text": (
            f"{title}\n\nTransformers revolutionized NLP. "
            "Self-attention allows parallel training on large corpora."
        ),
        "metadata": {"author": "Test Author", "date": "2024-01-15", "custom": []},
    }


@pytest.fixture
def mock_browsing_llm(monkeypatch):
    import core.library_service as lib
    import core.retrieval.page_chat as page_chat

    monkeypatch.setattr(
        lib,
        "_generate_summary",
        lambda page: f"Summary: {page.get('title', 'page')}",
    )
    monkeypatch.setattr(lib, "ingest_text", lambda **kwargs: {"id": "evt-e2e"})
    monkeypatch.setattr(lib, "remember_concept", lambda **kwargs: {"id": "concept:e2e"})
    monkeypatch.setattr(
        lib,
        "provider_chat",
        lambda messages, stream=False, max_tokens=None: (
            "Read the original paper\n"
            "Compare with RNN baselines\n"
            "What is attention?\n"
            "How does scaling change?\n"
            "Quiz me on the main idea"
        ),
    )
    monkeypatch.setattr(
        lib,
        "related_for_page",
        lambda page_url="", limit=8: [
            {"id": "concept:transformers", "name": "Transformers"},
        ],
    )

    def fake_ask(messages, stream=False, **kwargs):
        if stream:
            return iter(["Transformers ", "use ", "self-attention."])
        return "Transformers use self-attention."

    monkeypatch.setattr(page_chat, "provider_chat", fake_ask)


def test_e2e_browse_highlight_quote_chat_save_graph(
    backend_url,
    mock_browsing_llm,
):
    """Full side-panel journey on one page, then graph across two saved pages."""
    page_a = _sample_page(
        url="https://example.com/transformers",
        title="Understanding Transformers",
        selected="Self-attention allows parallel training",
    )
    page_b = _sample_page(
        url="https://example.com/scaling-laws",
        title="Scaling Laws for LLMs",
        selected="Performance improves predictably with scale",
    )

    # 1. Extension reads page context
    status, ctx = _request("POST", f"{backend_url}/page-context", page_a)
    assert status == 200
    assert ctx["page"]["url"] == page_a["url"]

    # 2. Save quote before page is saved (orphan quote flow)
    status, quote_res = _request("POST", f"{backend_url}/library/quotes", {
        "text": "Self-attention allows parallel training",
        "page_url": page_a["url"],
        "page_title": page_a["title"],
        "note": "Core insight",
    })
    assert status == 200
    quote_id = quote_res["quote"]["id"]

    status, listed = _request(
        "GET",
        f"{backend_url}/library/quotes?page_url={page_a['url']}",
    )
    assert status == 200
    assert len(listed["quotes"]) == 1

    # 3. Chat (streaming, like side panel)
    answer = _request_sse_post(f"{backend_url}/ask", {
        "question": "What is this page about?",
        "page": page_a,
        "history": [],
        "stream": True,
    })
    assert "self-attention" in answer.lower()
    history = [
        {"role": "user", "content": "What is this page about?"},
        {"role": "assistant", "content": answer},
    ]

    # 4. Follow-up with history
    follow_up = _request_sse_post(f"{backend_url}/ask", {
        "question": "Why does that matter?",
        "page": page_a,
        "history": history,
        "stream": True,
    })
    assert follow_up
    history.extend([
        {"role": "user", "content": "Why does that matter?"},
        {"role": "assistant", "content": follow_up},
    ])

    # 5. Save page with chat history
    status, saved = _request("POST", f"{backend_url}/library/save-page", {
        "page": page_a,
        "history": history,
    })
    assert status == 200
    page_id = saved["page"]["id"]
    assert saved["page"]["title"] == page_a["title"]
    assert saved["page"]["summary"]

    # 6. by-url lookup (syncPageLibraryState)
    status, by_url = _request(
        "GET",
        f"{backend_url}/library/by-url?url={page_a['url']}",
    )
    assert status == 200
    assert by_url["page"]["id"] == page_id
    assert len(by_url["page"]["chat_history"]) == 4

    # 7. Orphan quote linked after page save
    status, quotes = _request(
        "GET",
        f"{backend_url}/library/quotes?page_id={page_id}&page_url={page_a['url']}",
    )
    assert status == 200
    assert any(q["id"] == quote_id for q in quotes["quotes"])
    assert all(q.get("page_id") == page_id for q in quotes["quotes"])

    # 8. Second page + quote for graph
    _request("POST", f"{backend_url}/page-context", page_b)
    status, saved_b = _request("POST", f"{backend_url}/library/save-page", {
        "page": page_b,
        "history": [],
    })
    assert status == 200
    _request("POST", f"{backend_url}/library/quotes", {
        "text": "Performance improves predictably with scale",
        "page_id": saved_b["page"]["id"],
        "page_url": page_b["url"],
        "page_title": page_b["title"],
    })

    # 9. Graph view (saved tab)
    status, graph = _request("GET", f"{backend_url}/library/graph")
    assert status == 200
    page_nodes = [n for n in graph["nodes"] if n["type"] == "page"]
    assert len(page_nodes) >= 2
    assert not any(n["type"] == "quote" for n in graph["nodes"])
    assert any(e["type"] == "shared_topic" for e in graph["edges"])

    # 10. Explore suggestions
    status, explore = _request("POST", f"{backend_url}/library/explore", {"page": page_a})
    assert status == 200
    assert len(explore["suggestions"]) >= 3

    # 11. Edit quote
    status, patched = _request(
        "PATCH",
        f"{backend_url}/library/quotes/{quote_id}",
        {"text": "Self-attention enables parallel training", "note": "Updated"},
    )
    assert status == 200
    assert "enables" in patched["quote"]["text"]

    # 12. Delete quote (idempotent)
    status, _ = _request("DELETE", f"{backend_url}/library/quotes/{quote_id}")
    assert status == 200
    status, _ = _request("DELETE", f"{backend_url}/library/quotes/{quote_id}")
    assert status == 404

    # 13. Saved page detail still has chat
    status, detail = _request("GET", f"{backend_url}/library/pages/{page_id}")
    assert status == 200
    assert detail["page"]["title"] == page_a["title"]
    assert len(detail["page"]["chat_history"]) == 4
    assert detail["page"]["quotes"] == []


def test_e2e_library_clear_then_quotes_empty(backend_url, mock_browsing_llm):
    """Clear library should remove pages and quotes (extension stale-state guard)."""
    page = _sample_page(url="https://example.com/clear-flow", title="Clear flow")
    _request("POST", f"{backend_url}/library/quotes", {
        "text": "Quote to clear",
        "page_url": page["url"],
        "page_title": page["title"],
    })
    _request("POST", f"{backend_url}/library/save-page", {"page": page, "history": []})

    status, _ = _request("POST", f"{backend_url}/library/clear")
    assert status == 200

    status, pages = _request("GET", f"{backend_url}/library/pages")
    assert pages["pages"] == []

    status, quotes = _request("GET", f"{backend_url}/library/quotes?page_url={page['url']}")
    assert quotes["quotes"] == []

    status, graph = _request("GET", f"{backend_url}/library/graph")
    assert graph["nodes"] == []


def test_e2e_delete_saved_page(backend_url, mock_browsing_llm):
    """Delete a saved page via API (extension + dashboard parity)."""
    page = _sample_page(url="https://example.com/delete-me", title="Delete me")
    status, saved = _request("POST", f"{backend_url}/library/save-page", {
        "page": page,
        "history": [],
    })
    assert status == 200
    page_id = saved["page"]["id"]

    status, pages = _request("GET", f"{backend_url}/library/pages")
    assert any(p["id"] == page_id for p in pages["pages"])

    status, body = _request("DELETE", f"{backend_url}/library/pages/{page_id}")
    assert status == 200

    status, pages_after = _request("GET", f"{backend_url}/library/pages")
    assert not any(p["id"] == page_id for p in pages_after["pages"])
