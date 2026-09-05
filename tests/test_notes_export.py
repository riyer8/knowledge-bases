"""Round-trip fixtures for notes markdown ↔ :::quote bookshelf export."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "test_notes_export.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for notes export fixtures")
def test_notes_bookshelf_roundtrip():
    result = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "notes export round-trip ok" in result.stdout
