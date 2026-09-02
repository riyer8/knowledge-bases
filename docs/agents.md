# Agent Ownership

When multiple people or AI agents work in this repo, each module has one owner.
Do not modify another agent's module without explicit task scope.

| Module | Owner |
|---|---|
| `core/ingestion/` | ingestion-agent |
| `core/privacy/` | privacy-agent |
| `core/memory/` | memory-agent |
| `core/retrieval/` | retrieval-agent |
| `core/integrations/` | integration-agent |
| `core/proactive/` | proactive-agent |
| `DesktopApp/` | frontend-agent |
| `tests/`, eval harness | eval-agent |
| `core/config.py`, `main.py`, `core/frontend_backend.py` | infra-agent |

Cross-module interface changes require an entry in [decisions.md](decisions.md).

---

## ingestion-agent

**Owns:** `core/ingestion/`

**Responsibilities:** Screenshot OCR, text ingest, event writer. Emits raw events per
[event-schema](specs/event-schema.md). Must call privacy pipeline before storage.

**Must never:** Store events without privacy processing; bypass the ingestion contract.

**Tests:** `tests/test_ingestion.py`

---

## privacy-agent

**Owns:** `core/privacy/`

**Responsibilities:** PII detection, sensitive context auto-pause, name hashing, sensitivity
scoring. See [privacy-pipeline spec](specs/privacy-pipeline.md).

**Must never:** Log PII; weaken detection without updating eval cases; store plaintext names.

**Tests:** `tests/test_privacy.py`, `tests/test_privacy_eval_cases.py`

---

## memory-agent

**Owns:** `core/memory/`, `core/library_service.py`, `core/page_context_service.py`

**Responsibilities:** Chunking, embeddings, vector store, concept graph, bucket classifier,
saved library persistence.

**Tests:** `tests/test_concept_graph.py`, `tests/test_library_service.py`, `tests/test_page_context.py`

---

## retrieval-agent

**Owns:** `core/retrieval/`

**Responsibilities:** RAG chat, page chat, context assembly. Latency target: p95 < 2s.

**Tests:** `tests/test_retrieval.py`

---

## integration-agent

**Owns:** `core/integrations/`

**Responsibilities:** OAuth, GCal, Gmail read-only ingest. Emits events matching
[event-schema](specs/event-schema.md).

---

## proactive-agent

**Owns:** `core/proactive/`

**Responsibilities:** Pattern detection, ranked insights, proactive popup content.

---

## frontend-agent

**Owns:** `DesktopApp/`, `chrome-extension/`

**Responsibilities:** All user-facing clients. Thin HTTP clients — no business logic in UI.

---

## eval-agent

**Owns:** `tests/`, privacy eval fixtures

**Responsibilities:** Unit tests for side-effecting functions; higher-level eval suites
before module ship. Report failures in [status.md](status.md).

---

## infra-agent

**Owns:** `core/config.py`, `core/llm_service.py`, `core/llm_providers.py`,
`core/frontend_backend.py`, `main.py`, `scripts/`, `.env.example`, `requirements.txt`

**Responsibilities:** Config, LLM abstraction, HTTP routing (no business logic in router),
backend startup, launcher install scripts.

**Key interfaces:**
- `GET /health` — backend liveness
- All routes delegate to domain modules; router must not contain business logic

**Must never:** Hardcode paths or model names; add business logic to `frontend_backend.py`.

**Tests:** `tests/test_config.py`, `tests/test_llm_providers.py`, `tests/test_extension_api.py`

---

## Key cross-module interfaces

| Function | Module | Contract |
|---|---|---|
| `process(text, source, url?, ...)` | `core/privacy/pipeline.py` | Returns clean dict with `should_pause`, `text`, `entities`, `sensitivity_score` |
| `ingest_text(...)` | `core/ingestion/pipeline.py` | Raw → privacy → clean event storage |
| `save_page(page_data, ...)` | `core/library_service.py` | Persist explicit page save |
| `ask_with_context(...)` | `core/retrieval/page_chat.py` | Page-aware chat for extension |

Update this table when adding cross-module functions.
