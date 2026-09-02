# Project Status

_Last updated: 2026-09-02_

## Start here tomorrow

1. Read [constitution.md](constitution.md) — rules and doc index
2. Read this file — current phase and module health
3. Pick work from [roadmap.md](roadmap.md) (next: optional Slack integration or Phase 5)
4. Follow [init.md](../init.md) for session protocol

Quick health check:

```bash
pytest tests/ -q
curl http://127.0.0.1:8765/health
```

## Current phase

**Roadmap Phases 1–4 largely complete. Extension MVP + Desktop Life panel shipped.**

The Python backend on `localhost:8765` serves Chrome extension and macOS app. Storage is
unified at `~/.kb/`. Documentation lives entirely in `docs/`.

## Recently completed

- Buckets service + Life dashboard API (`/buckets/*`, `/dashboard/time`)
- Relationship profiles API with user editing (`/relationships/*`)
- iMessage read-only ingest (`/integrations/imessage/*`)
- Calendar time-context in RAG chat (`core/retrieval/time_context.py`)
- Life balance + relationship drift in proactive engine
- Desktop Life panel (time breakdown + people notes)
- Desktop chat with history + calendar context
- Configurable proactive cadence (Settings + env)
- Chrome extension proactive insight banner
- Chrome extension Settings tab (API keys, data controls, in-panel confirm dialogs)
- Page metadata (collapsible Details), editable quotes, page-centric graph
- Retrieval latency benchmark gate (`tests/test_retrieval_latency.py`)
- Screen capture importance flagging (⌘⇧I)
- Split `frontend_backend.py` into `core/http/` route modules
- Desktop Settings parity for API keys (`BackendSettingsStore`)
- **Wiki system** — raw ingest, LLM compile, health check, Q&A (`POST /wiki/ask`), web UI at `/app/`
- Chrome extension **Wiki** tab (+ Wiki button, ask-your-wiki)
- 173 unit and integration tests (run `pytest tests/ -q`)

## Next priorities

1. Optional Slack integration
2. Phase 5 external data (Amazon, Health, scraper — needs auth bridges)
3. Bucket override polish (filter by source, time range in extension)

## Active decisions

| Decision | Summary |
|---|---|
| Local-first at `~/.kb/` | No cloud sync; privacy is the product |
| Multi-provider LLM | `auto` prefers OpenAI when key set, else Ollama |
| Extension is a client | Backend owns memory; clients are thin |
| Launcher over native messaging | HTTP launcher on :8798 starts backend on :8765 |
| Docs in `docs/` only | `init.md` at root for session protocol; rules in `docs/constitution.md` |
| Desktop uses `/chat` | Extension uses `/ask` with page context; desktop uses memory-wide `/chat` |

Full rationale: [decisions.md](decisions.md)

## Module health

| Module | Status | Notes |
|---|---|---|
| `core/config.py` | done | proactive cadence config |
| `core/privacy/` | done | eval harness in tests |
| `core/ingestion/` | done | |
| `core/memory/` | done | buckets + relationships |
| `core/retrieval/` | done | calendar context + latency benchmark |
| `core/integrations/` | done | GCal, Gmail, iMessage |
| `core/proactive/` | done | engine + desktop + extension UI |
| `core/library_service.py` | done | |
| `chrome-extension/` | done | proactive banner + Life tab |
| `DesktopApp/` | done | library, life, chat with history |

## Known issues

- iMessage ingest requires macOS Full Disk Access for `~/Library/Messages/chat.db`
- Phase 5 integrations (Amazon, Health, scraper) intentionally deferred

## Blockers

None.
