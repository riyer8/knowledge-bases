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


def test_markdown_underscore_emphasis():
    html = _render_markdown("__bold__ and _italic_")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_markdown_bold_allows_inner_star():
    html = _render_markdown("**bold with a *star* inside**")
    assert "<strong>" in html and "</strong>" in html
    assert "**" not in html
    assert "<em>star</em>" in html


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


def test_markdown_ordered_list():
    html = _render_markdown("Intro:\n\n1. **First** — note\n2. **Second** — note")
    assert "<ol>" in html
    assert "<li><strong>First</strong>" in html
    assert "<li><strong>Second</strong>" in html


def test_markdown_splits_inline_numbered_list():
    html = _render_markdown(
        'Related: 1. **"Alpha"** - a. 2. **"Beta"** - b.'
    )
    assert "<ol>" in html
    assert html.count("<li>") == 2
    assert "<strong>&quot;Alpha&quot;</strong>" in html


def test_markdown_unicode_and_paren_lists():
    html = _render_markdown("• Alpha\n1) Beta\n2) Gamma")
    assert "<ul>" in html
    assert "<ol>" in html
    assert "<li>Alpha</li>" in html
    assert "<li>Beta</li>" in html


def test_markdown_list_continuation_indent():
    html = _render_markdown(
        "- **[Alpha](https://a.com)** — a.com\n  reason one\n- **[Beta](https://b.com)** — b.com"
    )
    assert html.count("<li>") == 2
    assert "reason one" in html
    assert "<li>reason one</li>" not in html


def test_markdown_demotes_latex_and_packed_headings():
    sample = (
        "We load vector \\( x \\) and \\( y \\). ### Breakdown: - **Loading**: "
        "- We load both. "
        "\\[ A = \\frac{\\text{Total FLOPs}}{\\text{Total Bytes}} = \\frac{2N - 1}{4N} \\] "
        "As \\( N \\to \\infty \\), \\( A \\approx \\frac{1}{2} \\)."
    )
    html = _render_markdown(sample)
    assert "\\(" not in html
    assert "\\[" not in html
    assert "\\frac" not in html
    assert "\\text" not in html
    assert "<h3>Breakdown:</h3>" in html
    assert "<strong>Loading</strong>" in html
    assert "(Total FLOPs)/(Total Bytes)" in html
    assert "(2N - 1)/(4N)" in html
    assert "→" in html
    assert "≈" in html


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
    ["--accent", "--bg", "--panel", "--text", "--success", "--danger", "--focus-ring", "--graph-node-fill"],
)
def test_design_tokens_present(token: str):
    content = WEB_TOKENS.read_text(encoding="utf-8")
    assert token in content
    assert '[data-theme-preference="light"]' in content
    assert '[data-theme="light"]' in content
    assert "@media (prefers-color-scheme: light)" in content
    root_block = content.split("[data-theme-preference=\"dark\"]")[0]
    assert "--accent:" in root_block
