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
├── wiki/                       # LLM-maintained markdown wiki
│   ├── raw/                    # Source documents (from saved pages, clips)
│   ├── articles/               # Compiled concept articles with [[wikilinks]]
│   ├── outputs/                # Generated slides, charts (future)
│   ├── index.md                # Auto-maintained index
│   └── manifest.json           # Compile tracking
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
| Extension `pageDraft:*` | Local-only notes until + Save | `chrome-extension/sidepanel/page-drafts.js` |
| `wiki/` | Mutable | `core/wiki_service.py` |
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
| Extension footer **Clear library** | Saved pages, quotes, per-page chats (`POST /library/clear`) |
| Extension footer **Delete all data** | Full `~/.kb/` wipe (`POST /delete-all`) |
| Desktop Settings **Clear Saved Library** | Same as `POST /library/clear` |
| Desktop Settings **Delete All Data** | Same as `POST /delete-all` |
| `POST /library/clear` | Saved pages, quotes, library graph only |
| `POST /delete-all` | Everything: events, index, graph, hashes, buckets, pages, relationships, OAuth tokens |

Backups are the user's responsibility — there is no cloud sync by design.
See [decisions.md](decisions.md) DECISION-001.

---

## Name anonymization

Stored text contains `[PERSON:hash]` tokens, not real names. The hash map at
`hashes/map.json` is used only at the UI/retrieval layer to render display names.
The LLM never receives the mapping. See [specs/name-anonymization.md](specs/name-anonymization.md).
