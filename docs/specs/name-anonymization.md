# Name Anonymization Spec

_Last updated: 2026-09-06_

## The Problem

The system passively captures communications and content involving real people.
We need to learn relationship patterns without the model ever learning that
"Ramya Iyer" is a specific real person tied to specific behaviors.

The solution: consistent pseudonymization at ingest, human-readable display at the UI layer.

---

## Design

```
                    ┌─────────────────────────┐
Raw text:           │ "Had coffee with Ramya"  │
                    └────────────┬────────────┘
                                 │
                         Privacy Pipeline
                                 │
                    ┌────────────▼────────────┐
Stored text:        │ "Had coffee with         │
                    │  [PERSON:a3f9b72c]"      │
                    └────────────┬────────────┘
                                 │
                         Hash Map Lookup
                                 │
                    ┌────────────▼────────────┐
Displayed to user:  │ "Had coffee with Ramya"  │
                    └─────────────────────────┘
```

The model only ever sees hashes. The user only ever sees names.

---

## Hash Map

Location: `~/.kb/hashes/map.json`

```json
{
  "a3f9b72c": {
    "display_name": "Ramya",
    "first_seen": "2026-05-19T14:32:00Z",
    "aliases": ["Ramya I.", "Ramya Iyer"],
    "user_edited": false
  }
}
```

- `display_name`: what the user sees (editable in Settings → Relationships)
- `first_seen`: when this person was first encountered
- `aliases`: all name variants that map to this hash
- `user_edited`: true if the user has manually set the display name

---

## Alias Merging

When a new name variant is detected:
1. Normalize: lowercase, strip punctuation
2. Compute hash
3. Check if any existing entry has a similar normalized form (Levenshtein distance < 2)
4. If match: add as alias to existing entry
5. If no match: create new entry

This prevents "Ramya" and "Ramya Iyer" from creating two separate profiles.

---

## User Editing

Users can:
- Change the display name for any hash ("Ramya" → "Ramya (work)")
- Merge two hashes if they realize they're the same person
- Split a hash if different people share a name
- All edits update the map.json file only — stored text is not re-processed

---

## Privacy Guarantees

- The hash map never leaves the device
- LLM prompts never include the hash map (the model never sees the mapping)
- Embeddings are computed on sanitized text with hashes, not names
- Relationship profiles reference hashes, not names

---

## What The LLM Sees

When answering a chat query, the retrieval layer assembles context. That context contains
sanitized text with hashes. The LLM generates a response with hashes. The response is
post-processed to replace hashes with display names before showing the user.

The LLM response therefore contains "[PERSON:a3f9b72c]" which becomes "Ramya" in the UI.
