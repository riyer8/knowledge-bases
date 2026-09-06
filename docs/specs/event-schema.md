# Event Schema

_Last updated: 2026-09-06_

All data flowing through the system is represented as events. This schema is the
contract between ingestion-agent and every downstream module.

---

## Raw Event (pre-privacy)

```json
{
  "id": "uuid-v4",
  "timestamp": "2026-05-19T14:32:00Z",
  "source": "screen_capture | manual_text | manual_file | manual_url | gcal | gmail | imessage",
  "content": {
    "text": "raw extracted text",
    "metadata": {}
  },
  "capture_context": {
    "app_name": "Safari",
    "window_title": "...",
    "url": "https://..."
  },
  "flagged_important": false,
  "raw_event": true
}
```

## Clean Event (post-privacy)

```json
{
  "id": "uuid-v4",
  "timestamp": "2026-05-19T14:32:00Z",
  "source": "screen_capture | manual_text | ...",
  "content": {
    "text": "sanitized text with hashed names",
    "metadata": {}
  },
  "capture_context": {
    "app_name": "Safari",
    "window_title": "...",
    "url": "https://..."
  },
  "flagged_important": false,
  "sensitivity_score": 0.3,
  "entities": [
    {"type": "PERSON", "hash": "a3f9b72c", "start": 12}
  ],
  "raw_event": false
}
```

---

## Field Definitions

| Field | Type | Description |
|---|---|---|
| `id` | string (uuid4) | Unique event identifier |
| `timestamp` | string (ISO 8601) | When the event was captured |
| `source` | string (enum) | Where the event came from |
| `content.text` | string | The text content (raw or sanitized) |
| `content.metadata` | object | Source-specific metadata |
| `capture_context` | object | App/window/URL at time of capture |
| `flagged_important` | boolean | User explicitly flagged this moment |
| `sensitivity_score` | float [0.0–1.0] | Post-privacy pipeline sensitivity rating |
| `entities` | array | Detected entities: `{type, hash, start}` (`PERSON` / `EMAIL` / `PHONE`) |
| `raw_event` | boolean | True = pre-privacy, False = post-privacy |

---

## Source-Specific Metadata

### screen_capture
```json
{ "duration_seconds": 30, "frame_count": 5 }
```

### manual_url
```json
{ "url": "https://...", "title": "Page title", "fetched": true }
```

### gcal
```json
{ "event_id": "...", "calendar": "Personal", "attendees_hashed": ["a3f9...", "b72c..."] }
```

### gmail
```json
{ "thread_id": "...", "subject": "...", "from_hashed": "a3f9...", "replied": false }
```

---

## Rules

1. Every event must have an `id` and `timestamp`
2. Raw events must never be read by memory-agent or retrieval-agent
3. Clean events must never contain unhashed personal names, emails, or phone numbers
4. `sensitivity_score` is required on all clean events
