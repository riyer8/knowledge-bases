from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from core.privacy.sensitive_sites import (
    SENSITIVE_APP_NAMES,
    SENSITIVE_DOMAINS,
    SENSITIVE_WINDOW_TITLE_KEYWORDS,
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"\b(?:\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b"
)

# spaCy loaded lazily so import doesn't fail if not installed yet
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy  # noqa: PLC0415
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


@dataclass
class DetectedEntity:
    entity_type: str   # PERSON | EMAIL | PHONE
    text: str
    start: int
    end: int


@dataclass
class PauseSignal:
    should_pause: bool
    pause_reason: Optional[str] = None


@dataclass
class DetectionResult:
    pause_signal: PauseSignal
    entities: list[DetectedEntity] = field(default_factory=list)


def check_sensitive_context(
    url: Optional[str],
    window_title: Optional[str],
    app_name: Optional[str],
) -> PauseSignal:
    """Return a pause signal if the capture context is sensitive."""
    if url:
        url_lower = url.lower()
        for domain in SENSITIVE_DOMAINS:
            if domain in url_lower:
                return PauseSignal(should_pause=True, pause_reason=f"sensitive url: {domain}")

    if window_title:
        title_lower = window_title.lower()
        for keyword in SENSITIVE_WINDOW_TITLE_KEYWORDS:
            if keyword in title_lower:
                return PauseSignal(should_pause=True, pause_reason=f"sensitive window title keyword: {keyword}")

    if app_name:
        app_lower = app_name.lower()
        for sensitive_app in SENSITIVE_APP_NAMES:
            if sensitive_app in app_lower:
                return PauseSignal(should_pause=True, pause_reason=f"sensitive app: {sensitive_app}")

    return PauseSignal(should_pause=False)


def detect_pii(text: str) -> list[DetectedEntity]:
    """Detect PERSON, EMAIL, and PHONE entities in text."""
    entities: list[DetectedEntity] = []

    # spaCy NER for PERSON entities
    nlp = _get_nlp()
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            entities.append(DetectedEntity(
                entity_type="PERSON",
                text=ent.text,
                start=ent.start_char,
                end=ent.end_char,
            ))

    # Regex for emails (spaCy misses some)
    for match in _EMAIL_RE.finditer(text):
        entities.append(DetectedEntity(
            entity_type="EMAIL",
            text=match.group(),
            start=match.start(),
            end=match.end(),
        ))

    # Regex for phone numbers
    for match in _PHONE_RE.finditer(text):
        entities.append(DetectedEntity(
            entity_type="PHONE",
            text=match.group(),
            start=match.start(),
            end=match.end(),
        ))

    # Sort by position, remove overlaps (keep first/longest match)
    entities.sort(key=lambda e: (e.start, -(e.end - e.start)))
    deduplicated: list[DetectedEntity] = []
    last_end = -1
    for entity in entities:
        if entity.start >= last_end:
            deduplicated.append(entity)
            last_end = entity.end

    return deduplicated
