# Privacy Pipeline Spec

_Last updated: 2026-09-06_

## Purpose

Every piece of data entering the system must pass through this pipeline before storage.
It is a mandatory, non-bypassable gate.

---

## Pipeline Steps (in order)

```
Raw Event
    ↓
1. Sensitive Context Detection
    ↓
2. PII Detection
    ↓
3. Name Hashing
    ↓
4. Text Sanitization
    ↓
5. Sensitivity Scoring
    ↓
Clean Event
```

---

## Step 1: Sensitive Context Detection

Checks the capture context (URL, app, window title) against known sensitive patterns.

**Triggers auto-pause if:**
- URL matches any entry in `sensitive_sites.py`
- Window title contains: "password", "login", "sign in", "credentials", "banking", "1password", "keychain"
- App name is: "1Password", "Keychain Access", "LastPass", "Bitwarden"
- Input field type is `password` (detected in screenshot via OCR patterns)

**Output:** `{ "should_pause": bool, "pause_reason": str | None }`

If `should_pause` is True:
- Emit pause signal to ingestion-agent
- Do NOT process or store the event
- Log the pause (without the content) to `~/.kb/events/paused.log`

---

## Step 2: PII Detection

Uses spaCy `en_core_web_sm` for named entity recognition.

**Detected entity types (stored / hashed today):**
- `PERSON` — personal names (spaCy NER)
- `EMAIL` — email addresses (regex)
- `PHONE` — phone numbers (regex)

**Output:** list of `DetectedEntity` with `entity_type`, `text`, `start`, `end`.
Clean-event records after sanitization are `{ "type", "hash", "start" }`.

---

## Step 3: Name Hashing

For each `PERSON` entity detected:
1. Normalize: lowercase, strip punctuation
2. Hash: `SHA-256(normalized_name + per_install_salt)`
3. Truncate hash to 8 chars for readability: `a3f9b72c`
4. Store in `~/.kb/hashes/map.json` as a rich entry, e.g.
   `{ "a3f9b72c": { "display_name": "Original Name", "first_seen": "...", "aliases": [], "user_edited": false } }`
5. Replace name in text with `[PERSON:a3f9b72c]`

**Per-install salt:**
- Generated on first hash in `core/privacy/hasher.py`: `secrets.token_hex(32)`
- Stored in `~/.kb/hashes/salt` (file permissions: 600)
- Never committed to git, never synced

**Hash consistency:**
- Same name always produces same hash (deterministic within an install)
- Different installs produce different hashes (the salt ensures this)

---

## Step 4: Text Sanitization

Replace detected PII in the text string:
- `PERSON` → `[PERSON:hash8]`
- `EMAIL` → `[EMAIL:hash8]`
- `PHONE` → `[PHONE:REDACTED]`

The sanitized text is what gets stored and embedded.

---

## Step 5: Sensitivity Scoring

Returns a float in [0.0, 1.0].

| Score | Meaning |
|---|---|
| 0.0–0.2 | Public/low sensitivity (news, reference material) |
| 0.2–0.5 | Normal personal content |
| 0.5–0.8 | Personal with PII (messages, emails) |
| 0.8–1.0 | High sensitivity (financial, health, credentials context) |

Scoring factors:
- Number of PII entities detected: +0.1 per entity, cap at 0.4
- Source type: `gmail` = +0.2, `imessage` = +0.2, `screen_capture` = +0.1
- Context keywords: "bank", "password", "health", "doctor" = +0.2 each
- `flagged_important`: no effect on sensitivity score

---

## Reverse Rendering (UI Layer)

Hashes are resolved back to display names before the user sees chat/retrieval output.
This happens in `core/retrieval/context_assembler.py` (`render_response` + `resolve_hash`),
not in a Swift `NameResolver`.

The hash map (`~/.kb/hashes/map.json`) is read-only from clients.
Display names can be edited via relationship profiles (`GET`/`POST /relationships/*`,
Desktop Life / Relationships UI).

---

## What Is Never Stored

- Raw screenshots (deleted after OCR extraction)
- Events from paused contexts
- Unhashed personal names in any indexed or stored content
- OAuth tokens (stored in `~/.kb/auth/`, not in events)
