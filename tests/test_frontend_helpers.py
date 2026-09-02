"""Unit tests for shared frontend helpers (markdown, theme tokens)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_JS = ROOT / "web" / "markdown.js"
THEME_JS = ROOT / "web" / "theme.js"
WEB_TOKENS = ROOT / "web" / "tokens.css"
EXT_TOKENS = ROOT / "chrome-extension" / "sidepanel" / "tokens.css"


def _node_eval(script: str) -> str:
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()


def _render_markdown(text: str) -> str:
    source = MARKDOWN_JS.read_text(encoding="utf-8")
    payload = json.dumps(text)
    return _node_eval(f"{source}\nconsole.log(renderMarkdown({payload}));")


def test_markdown_bold_and_italic():
    html = _render_markdown("**bold** and *italic*")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_markdown_escapes_html():
    html = _render_markdown("<script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_markdown_link_and_wikilink():
    html = _render_markdown("[Docs](https://example.com) and [[My Article]]")
    assert 'href="https://example.com"' in html
    assert 'data-wikilink="My Article"' in html


def test_markdown_codeblock():
    html = _render_markdown("```\nline one\n```")
    assert "<pre>" in html
    assert "line one" in html


def test_theme_modes_defined():
    source = THEME_JS.read_text(encoding="utf-8")
    assert '"system"' in source
    assert '"light"' in source
    assert '"dark"' in source
    assert "context-theme" in source


def test_tokens_css_synced_between_web_and_extension():
    web = WEB_TOKENS.read_text(encoding="utf-8")
    ext = EXT_TOKENS.read_text(encoding="utf-8")
    assert web == ext


@pytest.mark.parametrize(
    "token",
    ["--accent", "--bg", "--panel", "--text", "--success", "--danger", "--focus-ring"],
)
def test_design_tokens_present(token: str):
    content = WEB_TOKENS.read_text(encoding="utf-8")
    assert token in content
    assert "[data-theme=\"light\"]" in content
