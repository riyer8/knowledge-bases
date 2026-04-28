from __future__ import annotations

import shutil
from pathlib import Path

from core.graph_service import graph_dependencies_path


def delete_all_runtime_data(*, manual_root: Path, graph_root: Path, screenshot_root: Path) -> None:
    if manual_root.exists():
        shutil.rmtree(manual_root)

    dependencies_path = graph_dependencies_path(graph_root)
    if dependencies_path.exists():
        dependencies_path.unlink()

    if screenshot_root.exists():
        shutil.rmtree(screenshot_root)
