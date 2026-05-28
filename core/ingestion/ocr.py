from __future__ import annotations

import subprocess
from pathlib import Path


def extract_text(image_path: Path) -> str:
    """
    Extract text from a screenshot using macOS Vision OCR via a small Swift helper.
    Falls back to empty string if OCR fails — never crashes the ingestion pipeline.
    """
    if not image_path.exists():
        return ""

    try:
        result = subprocess.run(
            ["swift", str(Path(__file__).parent / "_ocr_helper.swift"), str(image_path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: try system `tesseract` if installed
    try:
        result = subprocess.run(
            ["tesseract", str(image_path), "stdout", "--psm", "3"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return ""
