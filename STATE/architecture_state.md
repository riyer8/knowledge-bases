# Architecture State

_Updated: 2026-08-30_

## Modules That Exist

| Module | Status | Notes |
|---|---|---|
| `core/config.py` | done | centralized path+env config |
| `core/privacy/` | done | detector, hasher, scorer, pipeline, sensitive_sites |
| `core/ingestion/` | done | pipeline, ocr, event_writer — screenshot + text ingest |
| `core/memory/` | done | chunker, vector_store, bucket_classifier, graph, concept_graph |
| `core/retrieval/` | done | chat (RAG), page_chat, context_assembler |
| `core/integrations/` | done | oauth, gcal, gmail — read-only |
| `core/proactive/` | done | detector, engine — ranked insights |
| `core/llm_providers.py` | done | OpenAI / Anthropic / Ollama abstraction |
| `core/llm_service.py` | done | legacy wrapper used by desktop `/chat` |
| `core/library_service.py` | done | saved pages, quotes, explore, library graph |
| `core/page_context_service.py` | done | page ingest, search, connections, remember |
| `core/frontend_backend.py` | done | unified HTTP router for all clients |
| `chrome-extension/` | done | side panel, page extract, native host auto-start |
| `DesktopApp/` | partial | chat, graph, pet, screenshots — not yet wired to `/library/*` |

## Storage Layout

Initialized at `~/.kb/` on first backend run. Key directories:

- `library/` — saved pages, quotes, per-page chats (extension)
- `pages/` — ephemeral page context
- `index/` — vector embeddings
- `graph/` — knowledge graph + concepts
- `events/` — raw and clean event logs

## Active Contracts

- `SPECS/event-schema.md` — event format
- `SPECS/privacy-pipeline.md` — privacy gate (mandatory)
- `SPECS/name-anonymization.md` — hash→display mapping

## Known Technical Debt

- Desktop app still uses legacy `/chat` and `/graph` — needs `/library/*` integration
- `core/` not yet extracted into planned `backend/` package
- Root `ARCHITECTURE.md` is a pointer; canonical doc is `docs/architecture.md`
- `STATE/current.md` was stale until this cleanup pass

## Documentation

Canonical docs live in `docs/`. See `docs/README.md` for the index.
