from __future__ import annotations

from core.privacy.detector import DetectedEntity

_SENSITIVE_KEYWORDS = frozenset({"bank", "banking", "password", "health", "doctor", "ssn", "insurance"})

_SOURCE_BONUSES: dict[str, float] = {
    "gmail": 0.2,
    "imessage": 0.2,
    "slack": 0.15,
    "screen_capture": 0.1,
}


def score(
    entities: list[DetectedEntity],
    source: str,
    text: str,
) -> float:
    """Return a sensitivity score in [0.0, 1.0]."""
    score_val = 0.0

    # PII entity count: +0.1 per entity, capped at 0.4
    pii_bonus = min(len(entities) * 0.1, 0.4)
    score_val += pii_bonus

    # Source type bonus
    score_val += _SOURCE_BONUSES.get(source.lower(), 0.0)

    # Keyword bonus (each matching keyword adds 0.2, uncapped here but clamped below)
    text_lower = text.lower()
    for keyword in _SENSITIVE_KEYWORDS:
        if keyword in text_lower:
            score_val += 0.2

    return min(round(score_val, 4), 1.0)
