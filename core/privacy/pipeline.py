from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from core.config import config
from core.privacy.detector import DetectedEntity, check_sensitive_context, detect_pii
from core.privacy.hasher import get_or_create_hash
from core.privacy.scorer import score


def _log_pause(pause_reason: str, source: str) -> None:
    config.paused_log.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    # Log only metadata — never the content of the paused event
    with config.paused_log.open("a") as f:
        f.write(f"{timestamp}\tpaused\tsource={source}\treason={pause_reason}\n")


def _sanitize_text(text: str, entities: list[DetectedEntity]) -> tuple[str, list[dict]]:
    """
    Replace detected entities in text with their anonymized tokens.
    Returns the sanitized text and a list of entity records (with hashes, not names).
    """
    # Process in reverse order so offsets stay valid
    sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)
    result = text
    entity_records: list[dict] = []

    for entity in sorted_entities:
        original = entity.text
        if entity.entity_type == "PERSON":
            h = get_or_create_hash(original)
            token = f"[PERSON:{h}]"
            entity_records.append({"type": "PERSON", "hash": h, "start": entity.start})
        elif entity.entity_type == "EMAIL":
            # Hash the email address itself
            import hashlib  # noqa: PLC0415
            h = hashlib.sha256(original.lower().encode()).hexdigest()[:8]
            token = f"[EMAIL:{h}]"
            entity_records.append({"type": "EMAIL", "hash": h, "start": entity.start})
        else:  # PHONE
            token = "[PHONE:REDACTED]"
            entity_records.append({"type": "PHONE", "hash": "REDACTED", "start": entity.start})

        result = result[: entity.start] + token + result[entity.end :]

    return result, entity_records


def process(
    text: str,
    source: str,
    url: Optional[str] = None,
    window_title: Optional[str] = None,
    app_name: Optional[str] = None,
    flagged_important: bool = False,
) -> dict:
    """
    Run a raw event through the full privacy pipeline.

    Always returns a complete output dict. If should_pause is True, the text
    is not processed — it is returned as an empty string.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Step 1: sensitive context check
    pause_signal = check_sensitive_context(url, window_title, app_name)
    if pause_signal.should_pause:
        _log_pause(pause_signal.pause_reason or "unknown", source)
        return {
            "text": "",
            "source": source,
            "url": url,
            "window_title": window_title,
            "app_name": app_name,
            "flagged_important": flagged_important,
            "sensitivity_score": 1.0,
            "entities": [],
            "should_pause": True,
            "pause_reason": pause_signal.pause_reason,
            "processed_at": timestamp,
        }

    # Step 2: PII detection
    entities = detect_pii(text)

    # Step 3 + 4: name hashing + text sanitization
    clean_text, entity_records = _sanitize_text(text, entities)

    # Step 5: sensitivity scoring
    sensitivity = score(entities, source, text)

    return {
        "text": clean_text,
        "source": source,
        "url": url,
        "window_title": window_title,
        "app_name": app_name,
        "flagged_important": flagged_important,
        "sensitivity_score": sensitivity,
        "entities": entity_records,
        "should_pause": False,
        "pause_reason": None,
        "processed_at": timestamp,
    }
