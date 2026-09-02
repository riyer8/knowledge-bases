# Storage Layout

All runtime data lives under **`~/.kb/`** (override with `KB_ROOT` in `.env`). Nothing in this
tree is committed to git.

---

## Directory map

```text
~/.kb/
├── library/                    # Extension + desktop saved reading library
│   ├── saved_pages.json        # Index of saved pages
│   ├── pages/{id}.json         # Page detail (title, url, summary)
│   ├── chats/{id}.jsonl        # Per-page chat history
│   └── quotes.json             # Highlighted quotes
├── pages/                      # Ephemeral page context from extension capture
├── events/
│   ├── raw/                    # Pre-privacy events (short TTL)
│   ├── clean/                  # Post-privacy events (append-only)
│   └── paused.log              # Pause metadata only — never content
├── index/                      # Vector embeddings for semantic search
├── graph/                      # Knowledge graph + concepts.json
├── hashes/
│   ├── map.json                # hash → display name (privacy layer)
│   └── salt                    # Write-once per install
├── buckets/
│   └── classifications.json    # Life bucket assignments (Phase 3)
└── auth/                       # OAuth tokens for integrations
```

---

## Who writes where

| Path | Rule | Module |
|---|---|---|
| `events/raw/` | Append-only | `core/ingestion/` |
| `events/clean/` | Append-only | `core/privacy/` |
| `events/paused.log` | Append-only, no PII | `core/privacy/` |
| `library/` | Mutable | `core/library_service.py` |
| `pages/` | Mutable | `core/page_context_service.py` |
| `index/` | Mutable | `core/memory/` |
| `graph/` | Mutable | `core/memory/` |
| `hashes/` | Mutable map; salt write-once | `core/privacy/` |
| `auth/` | Mutable | `core/integrations/` |
| `buckets/` | Mutable | `core/memory/` |

Violating write boundaries is a bug. See [constitution.md](constitution.md).

---

## Reset data

| Method | Scope |
|---|---|
| Extension footer **Clear all data** | Library + related memory |
| `POST /library/clear` | Saved pages, quotes, library graph |
| `POST /delete-all` | Broader wipe (desktop settings panel uses both) |

Backups are the user's responsibility — there is no cloud sync by design.
See [decisions.md](decisions.md) DECISION-001.

---

## Name anonymization

Stored text contains `[PERSON:hash]` tokens, not real names. The hash map at
`hashes/map.json` is used only at the UI/retrieval layer to render display names.
The LLM never receives the mapping. See [specs/name-anonymization.md](specs/name-anonymization.md).
