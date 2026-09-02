# Roadmap

Status key: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Shipped — Chrome Extension MVP

- [x] Side panel with page context extraction
- [x] Unified chat (`POST /ask`) with conversation history and streaming
- [x] Explicit page save + quote capture
- [x] Saved library (pages, quotes, explore, graph)
- [x] Knowledge graph (`core/memory/concept_graph.py`)
- [x] Semantic search (`GET /search`) and connections (`GET /connections`)
- [x] Launcher auto-start (`node scripts/install-launcher.mjs`)
- [x] Quotes | Chat tab UX in side panel
- [x] Proactive insight banner in side panel (`GET /proactive`)

API reference: [api.md](api.md)

---

## Phase 1 — Harden the Foundation

_Make what exists trustworthy before expanding._

- [x] Engineering constitution (`docs/constitution.md`) and session protocol (`init.md`)
- [x] Centralized config (`core/config.py`)
- [x] Privacy pipeline (`core/privacy/`)
  - [x] Sensitive URL / credential context detection
  - [x] Name detection and hashing
  - [x] Auto-pause signal
- [x] Ingestion pipeline (`core/ingestion/`)
- [x] Chunking + embeddings + semantic retrieval
- [x] Privacy eval harness (`tests/test_privacy_eval_cases.py`, 20+ cases)
- [x] Unit tests for core modules (`pytest tests/` — 150+ tests)
- [x] Screen capture with importance flagging (`POST /screenshot` + ⌘⇧I)
- [x] Desktop chat with conversation history and calendar context (`POST /chat`)

---

## Phase 2 — Integrations (Data In)

- [x] Google Calendar (OAuth + read-only ingest)
- [x] Gmail (OAuth + thread metadata ingest)
- [x] iMessage integration (local DB read — `core/integrations/imessage.py`)
- [x] Time-context for chat queries from calendar (`core/retrieval/time_context.py`)
- [ ] Slack integration (optional — deferred)

---

## Phase 3 — Buckets of Life + Relationships

Spec: [specs/buckets.md](specs/buckets.md)

- [x] Bucket taxonomy defined
- [x] `bucket_classifier` in `core/memory/`
- [x] Bucket API (`GET /buckets/*`, `POST /buckets/override`)
- [x] Tree view and time dashboard (`GET /buckets/tree`, `GET /dashboard/time`)
- [x] Desktop Life panel (time breakdown + relationship profiles)
- [x] Relationship profiles with user editing (`GET/POST /relationships/*`)
- [x] Auto-classification review UI in Chrome extension (`Life` tab + `POST /buckets/override`)

---

## Phase 4 — Proactive Bot

- [x] Detector + engine (`core/proactive/`)
- [x] Desktop proactive popup
- [x] Pending item detection (unanswered emails via Gmail)
- [x] Life balance pattern detection (`core/proactive/life_balance.py`)
- [x] Relationship drift alerts
- [x] Configurable pop-up cadence (Settings + `KB_PROACTIVE_INTERVAL_MINUTES`)
- [x] Browser-side proactive insights (extension banner)

---

## Phase 5 — External Data

- [x] Web content via Chrome extension (primary path)
- [ ] Amazon order history (deferred — needs auth strategy)
- [ ] Apple Health / Strava (deferred — HealthKit bridge)
- [ ] Research-topic web scraper (deferred)

---

## Ongoing

- [x] Keep [status.md](status.md) current after major sessions
- [x] Add eval suites before shipping new modules (see [testing.md](testing.md))
- [x] Retrieval latency benchmarks (`tests/test_retrieval_latency.py`, p95 < 2s)
- Keep [architecture.md](architecture.md) aligned with code
- Log non-obvious choices in [decisions.md](decisions.md)
