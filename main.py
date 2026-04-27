#!/usr/bin/env python3
"""Root launcher for backend services used by the DesktopApp frontend."""

from __future__ import annotations

from core.frontend_backend import main as run_frontend_backend


if __name__ == "__main__":
    run_frontend_backend()
