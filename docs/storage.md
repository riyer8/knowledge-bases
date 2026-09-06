# Storage Layout

_Last updated: 2026-09-06_

All runtime data lives under **`~/.kb/`** (override with `KB_ROOT` in `.env`). Nothing in this
tree is committed to git.

---

## Directory map

```text
~/.kb/
├── library/                    # Extension + desktop saved reading library
│   ├── saved_pages.json        # Index of saved pages
│   ├── pages/{id}.json         # Page detail (title, url, summary, metadata.notes)
│   ├── chats/{id}.jsonl        # Per-page chat history
│   └── quotes.json             # Highlight IDs / quote records
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
├── relationships/
│   └── profiles.json           # Editable person profiles
├── hashes/
│   ├── map.json                # hash → {display_name, first_seen, aliases, ...}
│   └── salt                    # Write-once per install (created on first hash)
├── buckets/
│   └── classifications.json    # Life bucket assignments
└── auth/                       # OAuth tokens for integrations
```

---

## Who writes where

| Path | Rule | Module |
|---|---|---|
| `events/raw/` | Append-only | `core/ingestion/event_writer.py` |
| `events/clean/` | Append-only (after privacy gate) | `core/ingestion/event_writer.py` |
| `events/paused.log` | Append-only, no PII | `core/privacy/` |
| `library/` | Mutable | `core/library_service.py` |
| Extension `pageDraft:*` | Local-only notes until + Save | `chrome-extension/sidepanel/page-drafts.js` |
| `wiki/` | Mutable | `core/wiki_service.py` |
| `pages/` | Mutable | `core/page_context_service.py` |
| `index/` | Mutable | `core/memory/` |
| `graph/` | Mutable | `core/memory/` |
| `relationships/` | Mutable | `core/memory/relationships.py` |
| `hashes/` | Mutable map; salt write-once on first hash | `core/privacy/hasher.py` |
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
| `POST /library/clear` | Saved pages, quotes, library chats only |
| `POST /delete-all` | Everything wiped by `delete_all_data()`: library, events, index, graph, hashes, buckets, pages, wiki, relationships, auth, paused.log |

Backups are the user's responsibility — there is no cloud sync by design.
See [decisions.md](decisions.md) DECISION-001.

---

## Name anonymization

Stored text contains `[PERSON:hash]` tokens, not real names. The hash map at
`hashes/map.json` maps each hash to an object (`display_name`, `first_seen`, `aliases`,
`user_edited`, …). Retrieval resolves tokens via `core/retrieval/context_assembler.py`
(`render_response` + `resolve_hash`). The LLM never receives the mapping.
See [specs/name-anonymization.md](specs/name-anonymization.md).
