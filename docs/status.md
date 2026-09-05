# Project Status

_Last updated: 2026-09-05_

## Start here tomorrow

1. Read [constitution.md](constitution.md) — rules and doc index
2. Read this file — current phase and module health
3. Pick work from [roadmap.md](roadmap.md) (reading loop polish, or later extras)
4. Follow [init.md](../init.md) for session protocol

Quick health check:

```bash
pytest tests/ -q
curl http://127.0.0.1:8765/health
```

## Current phase

**Reading-first.** The product loop is highlight → notes → bookshelf JSON → dashboard.

Life, Wiki, and integrations remain in the tree but are [archived from nav](archived.md). Phases 1–4 of the original Context roadmap are complete and parked.

The Python backend on `localhost:8765` serves Chrome extension and macOS app. Storage is
unified at `~/.kb/`. Documentation lives entirely in `docs/`.

## Recently completed

- Notes editor is the export source of truth (no quote-list seeding)
- Bookshelf JS object with `:::quote` fences matches the Notes document
- `metadata.dateAdded` persisted once on first save
- On-page highlight toolbar without requiring the side panel
- Dashboard and Saved views render `metadata.notes` (same document as the editor)
- Notes/export helpers extracted to `notes.js` / `bookshelf-export.js`

## Next priorities

1. Library-wide bookshelf export (array of entries)
2. Saved list filters (category, tags, medium)
3. Desktop library notes parity
4. Optional Slack / Phase 5 external data (still deferred)

## Active decisions

| Decision | Summary |
|---|---|
| Local-first at `~/.kb/` | No cloud sync; privacy is the product |
| Multi-provider LLM | `auto` prefers OpenAI when key set, else Ollama |
| Extension is a client | Backend owns memory; clients are thin |
| Notes own export | `metadata.notes` is what Copy JSON emits; `quotes.json` is highlight IDs |
| Life/Wiki archived | Hidden from nav; code stays. See [archived.md](archived.md) |

Full rationale: [decisions.md](decisions.md)

## Module health

| Module | Status | Notes |
|---|---|---|
| `core/library_service.py` | done | pages, quotes, `dateAdded` |
| `chrome-extension/` | in progress | reading loop is primary |
| `web/` | done | library shows notes + Copy JSON |
| `DesktopApp/` | parked | library still quote-list; follow-on |

## Known issues

- iMessage ingest requires macOS Full Disk Access for `~/Library/Messages/chat.db`
- PDF quotes save; on-page paint is HTML-only
- Phase 5 integrations (Amazon, Health, scraper) intentionally deferred

## Blockers

None.
