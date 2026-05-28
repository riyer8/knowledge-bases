from __future__ import annotations

import json
from pathlib import Path

from core.config import config
from core.llm_service import classify

# Flat list of all leaf buckets for LLM classification
_BUCKETS = [
    "Work/Deep Work",
    "Work/Meetings",
    "Work/Admin",
    "Work/Learning",
    "Relationships/Family",
    "Relationships/Friends",
    "Relationships/Colleagues",
    "Health/Exercise",
    "Health/Medical",
    "Health/Sleep",
    "Health/Food",
    "Finances/Transactions",
    "Finances/Investments",
    "Finances/Planning",
    "Home/Errands",
    "Home/Purchases",
    "Home/Maintenance",
    "Creativity/Projects",
    "Creativity/Exploration",
    "Entertainment/Media",
    "Entertainment/Social",
    "Other",
]

# Fast keyword rules — checked before hitting the LLM
_KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["standup", "sprint", "jira", "pull request", "code review", "deploy", "bug", "feature"], "Work/Deep Work"),
    (["meeting", "zoom", "call", "agenda", "sync", "1:1"], "Work/Meetings"),
    (["email", "inbox", "reply", "calendar invite", "schedule"], "Work/Admin"),
    (["course", "tutorial", "documentation", "lecture", "study"], "Work/Learning"),
    (["mom", "dad", "sister", "brother", "family", "parent"], "Relationships/Family"),
    (["friend", "hang out", "dinner with", "coffee with", "drinks with"], "Relationships/Friends"),
    (["colleague", "coworker", "manager", "report", "team"], "Relationships/Colleagues"),
    (["gym", "workout", "run", "yoga", "exercise", "steps", "miles"], "Health/Exercise"),
    (["doctor", "appointment", "prescription", "symptom", "hospital"], "Health/Medical"),
    (["sleep", "nap", "tired", "woke up", "bedtime"], "Health/Sleep"),
    (["lunch", "dinner", "breakfast", "recipe", "ate", "restaurant"], "Health/Food"),
    (["bank", "payment", "charge", "purchase", "spent", "paid"], "Finances/Transactions"),
    (["invest", "stock", "portfolio", "401k", "market"], "Finances/Investments"),
    (["budget", "savings", "financial plan", "expense"], "Finances/Planning"),
    (["errand", "grocery", "pickup", "drop off"], "Home/Errands"),
    (["bought", "order", "amazon", "delivery", "shipped"], "Home/Purchases"),
    (["repair", "maintenance", "fix", "cleaning", "lease"], "Home/Maintenance"),
    (["project", "build", "create", "design", "making"], "Creativity/Projects"),
    (["idea", "explore", "trying out", "experiment"], "Creativity/Exploration"),
    (["watch", "movie", "show", "podcast", "reading", "book"], "Entertainment/Media"),
    (["twitter", "instagram", "reddit", "scroll", "feed"], "Entertainment/Social"),
]


def _keyword_classify(text: str) -> str | None:
    lower = text.lower()
    for keywords, bucket in _KEYWORD_RULES:
        if any(kw in lower for kw in keywords):
            return bucket
    return None


def _source_classify(source: str, text: str) -> str | None:
    if source == "gcal":
        lower = text.lower()
        if any(w in lower for w in ["catch up", "1:1", "team", "sync"]):
            return "Work/Meetings"
        return "Work/Admin"
    return None


def _classifications_path() -> Path:
    return config.buckets_dir / "classifications.json"


def _load_classifications() -> dict:
    path = _classifications_path()
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_classifications(data: dict) -> None:
    config.buckets_dir.mkdir(parents=True, exist_ok=True)
    _classifications_path().write_text(json.dumps(data, indent=2))


def classify_event(event_id: str, text: str, source: str) -> str:
    """
    Classify an event into a life bucket.
    Uses rules first, falls back to LLM only when needed.
    Returns the bucket string (e.g. "Work/Deep Work").
    """
    classifications = _load_classifications()
    if event_id in classifications:
        return classifications[event_id]["bucket"]

    # 1. Source-based rules
    bucket = _source_classify(source, text)
    method = "source_rule"

    # 2. Keyword matching
    if not bucket:
        bucket = _keyword_classify(text)
        method = "keyword"

    # 3. LLM fallback
    if not bucket:
        bucket = classify(text[:500], _BUCKETS)
        method = "llm"
        # Guard against unexpected LLM output
        if bucket not in _BUCKETS:
            bucket = "Other"

    classifications[event_id] = {
        "bucket": bucket,
        "confidence": 1.0 if method != "llm" else 0.8,
        "source": method,
        "user_overridden": False,
    }
    _save_classifications(classifications)
    return bucket


def override_bucket(event_id: str, bucket: str) -> None:
    """User manually moves an event to a different bucket."""
    classifications = _load_classifications()
    entry = classifications.get(event_id, {})
    entry["bucket"] = bucket
    entry["source"] = "user_override"
    entry["user_overridden"] = True
    entry["confidence"] = 1.0
    classifications[event_id] = entry
    _save_classifications(classifications)
