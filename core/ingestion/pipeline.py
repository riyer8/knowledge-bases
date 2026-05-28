from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.config import config
from core.ingestion.event_writer import write_clean, write_raw
from core.ingestion.ocr import extract_text
from core.memory.store import ingest as memory_ingest
from core.privacy.pipeline import process as privacy_process


def ingest_screenshot(
    image_path: Path,
    window_title: Optional[str] = None,
    app_name: Optional[str] = None,
    url: Optional[str] = None,
    flagged_important: bool = False,
) -> dict:
    """
    Full pipeline for a screenshot:
    1. OCR → extract text
    2. Privacy pipeline → sanitize + check for pause
    3. Write raw event (then delete image)
    4. Write clean event
    5. Feed to memory (embed + classify + graph)
    Returns the clean event dict.
    """
    config.ensure_dirs()
    text = extract_text(image_path)

    # Always delete the raw image after OCR — never store screenshots
    try:
        image_path.unlink()
    except OSError:
        pass

    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    raw_event = {
        "id": event_id,
        "timestamp": timestamp,
        "source": "screen_capture",
        "content": {"text": text, "metadata": {"image_deleted": True}},
        "capture_context": {
            "app_name": app_name,
            "window_title": window_title,
            "url": url,
        },
        "flagged_important": flagged_important,
        "raw_event": True,
    }
    write_raw(raw_event)

    privacy_result = privacy_process(
        text=text,
        source="screen_capture",
        url=url,
        window_title=window_title,
        app_name=app_name,
        flagged_important=flagged_important,
    )

    if privacy_result["should_pause"]:
        return privacy_result

    clean_event = {
        "id": event_id,
        "timestamp": timestamp,
        "source": "screen_capture",
        "content": {"text": privacy_result["text"], "metadata": {}},
        "capture_context": {
            "app_name": app_name,
            "window_title": window_title,
            "url": url,
        },
        "flagged_important": flagged_important,
        "sensitivity_score": privacy_result["sensitivity_score"],
        "entities": privacy_result["entities"],
        "raw_event": False,
    }
    write_clean(clean_event)
    memory_ingest(clean_event)

    return clean_event


def ingest_text(
    text: str,
    source: str = "manual_text",
    metadata: Optional[dict] = None,
    flagged_important: bool = False,
) -> dict:
    """
    Ingest manually entered text, a URL fetch result, or any non-screenshot source.
    Same privacy + memory pipeline as screenshots.
    """
    config.ensure_dirs()
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    raw_event = {
        "id": event_id,
        "timestamp": timestamp,
        "source": source,
        "content": {"text": text, "metadata": metadata or {}},
        "capture_context": {},
        "flagged_important": flagged_important,
        "raw_event": True,
    }
    write_raw(raw_event)

    privacy_result = privacy_process(
        text=text,
        source=source,
        flagged_important=flagged_important,
    )

    if privacy_result["should_pause"]:
        return privacy_result

    clean_event = {
        "id": event_id,
        "timestamp": timestamp,
        "source": source,
        "content": {"text": privacy_result["text"], "metadata": metadata or {}},
        "capture_context": {},
        "flagged_important": flagged_important,
        "sensitivity_score": privacy_result["sensitivity_score"],
        "entities": privacy_result["entities"],
        "raw_event": False,
    }
    write_clean(clean_event)
    memory_ingest(clean_event)

    return clean_event
