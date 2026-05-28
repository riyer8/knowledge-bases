# Architecture State

_Updated: 2026-05-27_

## Modules That Exist

| Module | Status | Notes |
|---|---|---|
| `core/config.py` | done | centralized path+env config, `from core.config import config` |
| `core/privacy/` | done | detector, hasher, scorer, pipeline, sensitive_sites — full pipeline |
| `core/ingestion/` | done | pipeline, ocr, event_writer — screenshot + text ingest wired to privacy + memory |
| `core/memory/` | done | chunker, vector_store, bucket_classifier, graph, store |
| `core/retrieval/` | done | chat (RAG), context_assembler (hash→name rendering) ||
| `core/integrations/` | done | oauth.py, gcal.py, gmail.py — read-only, feeds ingestion pipeline |
| `core/proactive/` | done | detector.py (emails, calendar, drift), engine.py (ranked insights) |
| `core/llm_service.py` | exists | basic implementation, needs review against new architecture |
| `core/frontend_backend.py` | done | rewired to ingestion/retrieval/memory pipeline |
| `core/graph_service.py` | exists | basic graph, will be absorbed into memory-agent |
| `core/manual_input_service.py` | exists | basic manual input, will be absorbed into ingestion-agent |
| `core/data_reset_service.py` | exists | data reset logic |
| `inputs/screenshot/screenshot_service.py` | exists | precursor to ingestion-agent |
| `DesktopApp/` | exists | Swift/SwiftUI app with Chat, Graph, Settings, PetView |

## Storage Layout

No storage initialized yet. Will be created at `~/.kb/` on first run.

## Active Contracts

None yet. First contracts will be defined in `SPECS/event-schema.md` during Phase 1.

## Known Technical Debt

None yet (greenfield).
