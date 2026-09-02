#!/usr/bin/env python3
"""Live smoke test against a running backend (default http://127.0.0.1:8765)."""
from __future__ import annotations

import argparse
import json
import sys
from urllib import error, request


def api(method: str, base: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    data = headers = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
    req = request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E smoke test for KB backend")
    parser.add_argument("--base", default="http://127.0.0.1:8765", help="Backend base URL")
    args = parser.parse_args()
    base = args.base

    steps: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        steps.append((name, ok, detail))
        mark = "OK" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    status, health = api("GET", base, "/health")
    check("health", status == 200 and health.get("ok"), health.get("storage", ""))

    # Detect stale backend processes missing library DELETE routes.
    route_status, route_body = api(
        "DELETE",
        base,
        "/library/quotes/00000000-0000-4000-8000-000000000000",
    )
    routes_ok = route_status == 404 and route_body.get("error") == "quote not found"
    check(
        "library delete route",
        routes_ok,
        "restart backend (python3 main.py) if this fails",
    )
    if not routes_ok:
        failed = [name for name, ok, _ in steps if not ok]
        print(f"\nFAILED: {', '.join(failed)}")
        return 1

    page = {
        "url": "https://example.com/e2e-smoke",
        "title": "E2E Smoke Page",
        "site": "example.com",
        "headings": ["Intro"],
        "paragraphs": ["Smoke test paragraph about knowledge bases."],
        "visible_text": "Smoke test content for end-to-end validation.",
        "page_type": "article",
        "metadata": {"author": "", "date": "", "custom": []},
    }

    status, ctx = api("POST", base, "/page-context", page)
    check("page-context", status == 200, ctx.get("page", {}).get("id", ""))

    status, quote = api("POST", base, "/library/quotes", {
        "text": "Smoke test quote from highlight",
        "page_url": page["url"],
        "page_title": page["title"],
    })
    quote_id = quote.get("quote", {}).get("id", "")
    check("save quote", status == 200 and bool(quote_id))

    status, ask = api("POST", base, "/ask", {
        "question": "What is this page about?",
        "page": page,
        "stream": False,
    })
    check("ask", status == 200 and bool(ask.get("reply")), (ask.get("reply") or "")[:60])

    status, saved = api("POST", base, "/library/save-page", {
        "page": page,
        "history": [
            {"role": "user", "content": "What is this page about?"},
            {"role": "assistant", "content": ask.get("reply", "")},
        ],
    })
    page_id = saved.get("page", {}).get("id", "")
    check("save page", status == 200 and bool(page_id))

    status, graph = api("GET", base, "/library/graph")
    page_nodes = [n for n in graph.get("nodes", []) if n.get("type") == "page"]
    check("graph", status == 200 and len(page_nodes) >= 1, f"{len(page_nodes)} page nodes")

    if quote_id:
        status, body = api("DELETE", base, f"/library/quotes/{quote_id}")
        check("delete quote", status == 200, body.get("error", ""))

    failed = [name for name, ok, _ in steps if not ok]
    print()
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
