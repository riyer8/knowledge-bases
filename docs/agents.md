# Agent Ownership

_Last updated: 2026-09-06_

When multiple people or AI agents work in this repo, each module has one owner.
Do not modify another agent's module without explicit task scope.

| Module | Owner |
|---|---|
| `core/ingestion/` | ingestion-agent |
| `core/privacy/` | privacy-agent |
| `core/memory/`, `core/library_service.py`, `core/page_context_service.py`, `core/wiki_service.py` | memory-agent |
| `core/retrieval/` | retrieval-agent |
| `core/integrations/` | integration-agent |
| `core/proactive/` | proactive-agent |
| `DesktopApp/`, `chrome-extension/`, `web/` | frontend-agent |
| `tests/`, eval harness | eval-agent |
| `core/config.py`, `core/env_settings.py`, `core/http/`, `core/frontend_backend.py`, `core/llm_service.py`, `core/llm_providers.py`, `main.py`, `scripts/` | infra-agent |

Cross-module interface changes require an entry in [decisions.md](decisions.md).

---

## ingestion-agent

**Owns:** `core/ingestion/`

**Responsibilities:** Screenshot OCR, text ingest, event writer (`write_raw` / `write_clean`).
Emits raw events per [event-schema](specs/event-schema.md). Must call privacy pipeline before
persisting clean events.

**Must never:** Store events without privacy processing; bypass the ingestion contract.

**Tests:** `tests/test_ingestion.py`

---

## privacy-agent

**Owns:** `core/privacy/`

**Responsibilities:** PII detection, sensitive context auto-pause, name hashing, sensitivity
scoring. See [privacy-pipeline spec](specs/privacy-pipeline.md).

**Must never:** Log PII; weaken detection without updating eval cases; store plaintext names
outside the hash map.

**Tests:** `tests/test_privacy.py`, `tests/test_privacy_eval_cases.py`

---

## memory-agent

**Owns:** `core/memory/`, `core/library_service.py`, `core/page_context_service.py`,
`core/wiki_service.py`

**Responsibilities:** Chunking, embeddings, vector store, concept graph, bucket classifier,
relationship profiles, saved library persistence (including notes metadata / PDF extract),
wiki raw/compile/ask.

**Tests:** `tests/test_memory.py`, `tests/test_concept_graph.py`, `tests/test_library_service.py`,
`tests/test_library_documents.py`, `tests/test_page_context.py`, `tests/test_buckets_service.py`,
`tests/test_relationships.py`, `tests/test_wiki_service.py`

---

## retrieval-agent

**Owns:** `core/retrieval/`

**Responsibilities:** RAG chat, page chat (`ask_about_page`), context assembly / hash rendering.
Latency target: p95 < 2s.

**Tests:** `tests/test_retrieval.py`, `tests/test_retrieval_latency.py`, `tests/test_time_context.py`

---

## integration-agent

**Owns:** `core/integrations/`

**Responsibilities:** OAuth, GCal, Gmail, iMessage read-only ingest. Emits events matching
[event-schema](specs/event-schema.md).

**Tests:** `tests/test_integrations.py`, `tests/test_imessage.py`

---

## proactive-agent

**Owns:** `core/proactive/`

**Responsibilities:** Pattern detection, ranked insights for desktop pet / proactive popup.

**Tests:** `tests/test_proactive.py`

---

## frontend-agent

**Owns:** `DesktopApp/`, `chrome-extension/`, `web/`

**Responsibilities:** All user-facing clients. Thin HTTP clients — no business logic in UI.
Reading loop (notes / bookshelf export) lives primarily in the extension + dashboard.

**Tests:** `tests/test_frontend_helpers.py`, `tests/test_notes_export.py` (+ `.js`),
`tests/test_page_drafts.js`, `tests/test_e2e_browsing_flow.py`, `scripts/e2e_browser_smoke.mjs`

---

## eval-agent

**Owns:** `tests/`, privacy eval fixtures

**Responsibilities:** Unit tests for side-effecting functions; higher-level eval suites
before module ship. Report failures in [status.md](status.md).

---

## infra-agent

**Owns:** `core/config.py`, `core/env_settings.py`, `core/http/`, `core/llm_service.py`,
`core/llm_providers.py`, `core/frontend_backend.py`, `main.py`, `scripts/`, `.env.example`,
`requirements.txt`, `package.json`, `start.sh` / `stop.sh`

**Responsibilities:** Config, LLM abstraction, HTTP routing (no business logic in router),
backend startup, launcher / e2e / install scripts.

**Key interfaces:**
- `GET /health` — backend liveness
- All routes delegate to domain modules; router must not contain business logic

**Must never:** Hardcode paths or model names; add business logic to `frontend_backend.py`.

**Tests:** `tests/test_config.py`, `tests/test_env_settings.py`, `tests/test_llm_providers.py`,
`tests/test_extension_api.py`, `tests/test_data_reset.py`, `tests/test_native_host.py`

---

## Key cross-module interfaces

| Function | Module | Contract |
|---|---|---|
| `process(text, source, url?, ...)` | `core/privacy/pipeline.py` | Returns clean dict with `should_pause`, `text`, `entities`, `sensitivity_score` |
| `ingest_text(...)` | `core/ingestion/pipeline.py` | Raw → privacy → clean event storage via `event_writer` |
| `write_clean(event)` | `core/ingestion/event_writer.py` | Append clean event JSONL under `events/clean/` |
| `save_page(page_data, ...)` | `core/library_service.py` | Persist explicit page save (incl. normalized metadata/notes) |
| `ask_about_page(question, page, *, history, stream, saved_page_id)` | `core/retrieval/page_chat.py` | Page-aware chat for extension |
| `render_response(text)` | `core/retrieval/context_assembler.py` | Resolve `[PERSON:hash]` tokens for UI |

Update this table when adding cross-module functions.
