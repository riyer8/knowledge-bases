# Project Status

_Last updated: 2026-09-09_

## Start here tomorrow

1. Read [constitution.md](constitution.md) — rules and doc index
2. Read this file — current phase and module health
3. Pick work from [roadmap.md](roadmap.md) (reading loop polish, or later extras)
4. Follow [init.md](../init.md) for session protocol (Cursor agents also get [AGENTS.md](../AGENTS.md))

Quick health check:

```bash
pytest tests/ -q
curl http://127.0.0.1:8765/health
```

## Current phase

**Reading-first.** The product loop is highlight → notes → bookshelf JSON → dashboard.

Life, Wiki, and integrations remain in the tree but are [archived from nav](archived.md). Phases 1–4 of the original Context roadmap are complete and parked.

The Python backend on `localhost:8765` serves Chrome extension and macOS app. Storage is
unified at `~/.kb/`. Documentation lives entirely in `docs/` (plus root `init.md` / `AGENTS.md`).

Public repo hardening (2026-09-09): MIT license, expanded root README, `.env.example` completeness,
git-history secret scan. No product behavior changes.

## Recently completed

- **Public repo hardening (2026-09-09):** MIT `LICENSE`, expanded root `README.md` (setup + screenshots + env-dependent tests), `.env.example` covers launcher/`CONTEXT_REPO_ROOT` vars. gitleaks 8.24.3 + trufflehog 3.88.27: no secrets in git history.
- **Docs haul (2026-09-06):** aligned markdown with code (architecture, API, storage, agents, design, specs, init/constitution mutation tables). Code remains source of truth.
- Notes editor is the export source of truth (no quote-list seeding)
- Bookshelf JS object with `:::quote` fences matches the Notes document
- `metadata.dateAdded` persisted once on first save
- On-page highlight toolbar without requiring the side panel
- Dashboard and Saved views render `metadata.notes` (same document as the editor)
- Notes/export helpers extracted to `notes.js` / `bookshelf-export.js`
- Root `AGENTS.md` so Cursor agents load `init.md`

## Next priorities

1. Extension trust + UX — see [extension-pitfalls-and-next.md](extension-pitfalls-and-next.md) (Sprint A–B first)
2. Library-wide bookshelf export (array of entries)
3. Saved list filters (category, tags, medium)
4. Desktop library notes parity (Context.app — Sprint D; after Sprint A)

Detailed backlog of pitfalls, file map, and success criteria: **[extension-pitfalls-and-next.md](extension-pitfalls-and-next.md)**.

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
| `core/library_service.py` | done | pages, quotes, notes metadata, PDF extract, `dateAdded` |
| `chrome-extension/` | in progress | reading loop is primary |
| `web/` | done | library shows notes + Copy JSON |
| `DesktopApp/` | parked | library still quote-list; follow-on |
| `docs/` | refreshed | public README/LICENSE 2026-09-09; matched to code 2026-09-06 |

## Known issues

- iMessage ingest requires macOS Full Disk Access for `~/Library/Messages/chat.db`
- PDF quotes save; on-page paint is HTML-only
- Phase 5 integrations (Amazon, Health, scraper) intentionally deferred
- Desktop library notes parity still open (Sprint D)
- `pytest tests/test_integrations.py::test_gmail_sync_ingests_threads` hits the live LLM during ingest (Ollama if no OpenAI key; OpenAI if `.env` has one). Environmental, not a product bug — documented in root README.

## Recently hardened (extension 0.1.8)

- Title field: single-line normalize, no giant-gap autosize
- Notes: Enter/Backspace quote contract, typed `>` manual quotes, markdown headings/lists round-trip
- Copy JSON: `:::quote` fences; manual quotes do not paint on the page
- Backend `_normalize_title` on save/update/get (restart backend to load)
- Browser smoke: `npm install` then `node scripts/e2e_browser_smoke.mjs` (see [testing.md](testing.md))

## Blockers

None.
