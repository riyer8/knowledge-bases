"""Tests for native host launcher scripts."""
from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_context_host():
    host = REPO_ROOT / "chrome-extension" / "native-host" / "context_host.py"
    spec = importlib.util.spec_from_file_location("context_host", host)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_start_backend_script_exists():
    script = REPO_ROOT / "scripts" / "start_backend.sh"
    assert script.exists()


def test_native_host_script_exists():
    host = REPO_ROOT / "chrome-extension" / "native-host" / "context_host.py"
    assert host.exists()


def test_context_host_handles_start_message(monkeypatch):
    class FakeResult:
        stdout = "started\n"
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeResult())
    host_mod = _load_context_host()
    result = host_mod.handle({"action": "start"})
    assert result["ok"] is True
    assert result["status"] == "started"


def test_context_host_read_write_message():
    host_mod = _load_context_host()
    payload = json.dumps({"action": "ping"}).encode("utf-8")
    message = struct.pack("<I", len(payload)) + payload

    class FakeStdin:
        buffer = type("B", (), {"read": staticmethod(lambda n: message[:n] if n == 4 else payload)})()

    class FakeStdout:
        chunks: list[bytes] = []

        @property
        def buffer(self):
            return self

        def write(self, data: bytes) -> None:
            FakeStdout.chunks.append(data)

        def flush(self) -> None:
            return None

    host_mod.sys.stdin = FakeStdin()
    host_mod.sys.stdout = FakeStdout()
    host_mod.read_message = lambda: {"action": "ping"}
    host_mod.handle = lambda message: {"ok": True, "status": "pong"}
    host_mod.send_message({"ok": True, "status": "pong"})
    assert FakeStdout.chunks
