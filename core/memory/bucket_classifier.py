from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from core.config import config
from core.llm_service import classify

# Reading-first taxonomy. Leaves may be "Parent/Child" or a top-level name.
_BUCKETS = [
    "Work/Projects",
    "Work/Meetings",
    "Work/Admin",
    "Learning/Research",
    "Learning/Tutorials",
    "Learning/Reference",
    "News",
    "People/Family",
    "People/Friends",
    "People/Colleagues",
    "Health/Fitness",
    "Health/Medical",
    "Health/Food",
    "Money/Spending",
    "Money/Investing",
    "Money/Planning",
    "Home",
    "Creative",
    "Entertainment",
    "Other",
]

_TOP_LEVEL_ORDER = list(dict.fromkeys(b.split("/", 1)[0] for b in _BUCKETS))

_LEGACY_BUCKETS = {
    "Work/Deep Work": "Work/Projects",
    "Work/Learning": "Learning/Tutorials",
    "Relationships/Family": "People/Family",
    "Relationships/Friends": "People/Friends",
    "Relationships/Colleagues": "People/Colleagues",
    "Health/Exercise": "Health/Fitness",
    "Health/Sleep": "Health/Medical",
    "Finances/Transactions": "Money/Spending",
    "Finances/Investments": "Money/Investing",
    "Finances/Planning": "Money/Planning",
    "Home/Errands": "Home",
    "Home/Purchases": "Home",
    "Home/Maintenance": "Home",
    "Creativity/Projects": "Creative",
    "Creativity/Exploration": "Creative",
    "Entertainment/Media": "Entertainment",
    "Entertainment/Social": "Entertainment",
}

# Host suffix → bucket. Checked before keywords so articles classify by site.
_URL_RULES: list[tuple[tuple[str, ...], str]] = [
    (("github.com", "gitlab.com", "bitbucket.org", "linear.app", "atlassian.net"), "Work/Projects"),
    (("meet.google.com", "zoom.us", "teams.microsoft.com"), "Work/Meetings"),
    (("mail.google.com", "outlook.office.com", "outlook.live.com"), "Work/Admin"),
    (("arxiv.org", "scholar.google.com", "pubmed.ncbi.nlm.nih.gov", "jstor.org"), "Learning/Research"),
    (("coursera.org", "udemy.com", "khanacademy.org", "edx.org", "skillshare.com"), "Learning/Tutorials"),
    (("developer.mozilla.org", "docs.python.org", "learn.microsoft.com", "devdocs.io"), "Learning/Reference"),
    (
        (
            "nytimes.com",
            "bbc.com",
            "bbc.co.uk",
            "cnn.com",
            "reuters.com",
            "theguardian.com",
            "apnews.com",
            "washingtonpost.com",
            "wsj.com",
            "ft.com",
            "theverge.com",
            "techcrunch.com",
            "arstechnica.com",
            "npr.org",
            "bloomberg.com",
        ),
        "News",
    ),
    (("webmd.com", "mayoclinic.org", "nih.gov", "who.int"), "Health/Medical"),
    (("strava.com", "myfitnesspal.com", "peloton.com"), "Health/Fitness"),
    (("allrecipes.com", "seriouseats.com", "epicurious.com"), "Health/Food"),
    (("robinhood.com", "fidelity.com", "vanguard.com", "coindesk.com"), "Money/Investing"),
    (("mint.com", "paypal.com", "venmo.com"), "Money/Spending"),
    (("netflix.com", "spotify.com", "youtube.com", "twitch.tv", "hulu.com"), "Entertainment"),
    (("x.com", "twitter.com", "instagram.com", "reddit.com", "tiktok.com", "facebook.com"), "Entertainment"),
    (("amazon.com", "ebay.com", "ikea.com", "homedepot.com"), "Home"),
    (("figma.com", "behance.net", "dribbble.com"), "Creative"),
]

# Specific phrases only — generic words like "reading" or "email" misfire on articles.
_KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["zoom meeting", "standup", "sprint planning", "1:1", "sync with"], "Work/Meetings"),
    (["pull request", "code review", "jira", "ci/cd", "merge request"], "Work/Projects"),
    (["inbox zero", "expense report", "timesheet", "calendar invite"], "Work/Admin"),
    (["arxiv", "whitepaper", "literature review", "peer-reviewed"], "Learning/Research"),
    (["tutorial", "how-to", "walkthrough", "course lecture"], "Learning/Tutorials"),
    (["api reference", "official docs", "man page"], "Learning/Reference"),
    (["breaking news", "reported that"], "News"),
    (["mom", "dad", "sister", "brother", "family dinner"], "People/Family"),
    (["hang out", "dinner with", "coffee with", "drinks with"], "People/Friends"),
    (["colleague", "coworker", "direct report"], "People/Colleagues"),
    (["gym", "workout", "yoga", "5km", "5 km", "morning run", "went for a run", "for a run", "run this"], "Health/Fitness"),
    (["doctor", "prescription", "hospital", "appointment"], "Health/Medical"),
    (["recipe", "restaurant", "breakfast", "lunch", "dinner"], "Health/Food"),
    (["bank statement", "credit card", "venmo"], "Money/Spending"),
    (["401k", "stock portfolio", "index fund"], "Money/Investing"),
    (["budget", "savings goal", "financial plan"], "Money/Planning"),
    (["grocery", "groceries", "errand", "lease", "landlord"], "Home"),
    (["figma", "sketch", "illustration"], "Creative"),
    (["netflix", "podcast episode", "watched"], "Entertainment"),
]


def normalize_bucket(bucket: str) -> str:
    mapped = _LEGACY_BUCKETS.get(bucket, bucket)
    return mapped if mapped in _BUCKETS else "Other"


def _keyword_classify(text: str) -> str | None:
    lower = text.lower()
    for keywords, bucket in _KEYWORD_RULES:
        if any(kw in lower for kw in keywords):
            return bucket
    return None


def _host_matches(host: str, needle: str) -> bool:
    host = host.lower().removeprefix("www.")
    needle = needle.lower()
    return host == needle or host.endswith("." + needle)


def _url_classify(url: str) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc
    except ValueError:
        return None
    if not host:
        return None
    for hosts, bucket in _URL_RULES:
        if any(_host_matches(host, needle) for needle in hosts):
            return bucket
    return None


def _extract_url(text: str, url: str = "") -> str:
    if url.strip():
        return url.strip()
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("url:"):
            return stripped.split(":", 1)[1].strip()
        if stripped.startswith("http://") or stripped.startswith("https://"):
            return stripped.split()[0]
    return ""


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
        data = json.loads(path.read_text())
    else:
        data = {}
    changed = False
    for meta in data.values():
        if not isinstance(meta, dict):
            continue
        old = str(meta.get("bucket", "Other"))
        new = normalize_bucket(old)
        if new != old:
            meta["bucket"] = new
            changed = True
    if changed:
        _save_classifications(data)
    return data


def _save_classifications(data: dict) -> None:
    config.buckets_dir.mkdir(parents=True, exist_ok=True)
    _classifications_path().write_text(json.dumps(data, indent=2))


def classify_event(event_id: str, text: str, source: str, url: str = "") -> str:
    """
    Classify an event into a life bucket.
    Uses URL and rules first, falls back to LLM only when needed.
    Returns the bucket string (e.g. "Work/Projects").
    """
    classifications = _load_classifications()
    if event_id in classifications:
        return normalize_bucket(str(classifications[event_id].get("bucket", "Other")))

    resolved_url = _extract_url(text, url)

    bucket = _url_classify(resolved_url)
    method = "url_rule"

    if not bucket:
        bucket = _source_classify(source, text)
        method = "source_rule"

    if not bucket:
        bucket = _keyword_classify(text)
        method = "keyword"

    if not bucket:
        bucket = classify(text[:500], _BUCKETS)
        method = "llm"
        bucket = normalize_bucket(bucket)

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
    bucket = normalize_bucket(bucket)
    classifications = _load_classifications()
    entry = classifications.get(event_id, {})
    entry["bucket"] = bucket
    entry["source"] = "user_override"
    entry["user_overridden"] = True
    entry["confidence"] = 1.0
    classifications[event_id] = entry
    _save_classifications(classifications)


def remove_classifications(event_ids: set[str]) -> None:
    if not event_ids:
        return
    classifications = _load_classifications()
    changed = False
    for event_id in event_ids:
        if event_id in classifications:
            del classifications[event_id]
            changed = True
    if changed:
        _save_classifications(classifications)
