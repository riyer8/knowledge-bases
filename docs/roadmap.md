# Roadmap

Status key: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Shipped — Chrome Extension MVP

- [x] Side panel with page context extraction
- [x] Unified chat (`POST /ask`) with conversation history
- [x] Explicit page save + quote capture
- [x] Saved library (pages, quotes, explore, graph)
- [x] Knowledge graph (`core/memory/concept_graph.py`)
- [x] Semantic search (`GET /search`) and connections (`GET /connections`)
- [x] Launcher auto-start (`node scripts/install-launcher.mjs`)
- [x] Quotes | Chat tab UX in side panel

API reference: [api.md](api.md)

---

## Phase 1 — Harden the Foundation

_Make what exists trustworthy before expanding._

- [x] Engineering constitution (`CLAUDE.md`) and session protocol (`init.md`)
- [x] Centralized config (`core/config.py`)
- [x] Privacy pipeline (`core/privacy/`)
  - [x] Sensitive URL / credential context detection
  - [x] Name detection and hashing
  - [x] Auto-pause signal
- [x] Ingestion pipeline (`core/ingestion/`)
- [x] Chunking + embeddings + semantic retrieval
- [x] Privacy eval harness (`tests/test_privacy_eval_cases.py`, 20+ cases)
- [x] Unit tests for core modules (`pytest tests/`)

- [~] Screen capture polish (menu bar controls, importance flagging)
- [~] Desktop app parity with extension (`/library/*` done; `/ask` pending)

---

## Phase 2 — Integrations (Data In)

- [x] Google Calendar (OAuth + read-only ingest)
- [x] Gmail (OAuth + thread metadata ingest)
- [ ] iMessage integration (local DB read)
- [ ] Slack integration (optional)
- [ ] Time-context for chat queries from calendar

---

## Phase 3 — Buckets of Life + Relationships

Spec: [specs/buckets.md](specs/buckets.md)

- [x] Bucket taxonomy defined
- [x] `bucket_classifier` in `core/memory/`
- [ ] Auto-classification UI
- [ ] Tree view (filter by time, bucket, activity)
- [ ] Relationship profiles with user editing
- [ ] "How I spend my time" dashboard

---

## Phase 4 — Proactive Bot

- [x] Detector + engine (`core/proactive/`)
- [x] Desktop proactive popup (basic)
- [ ] Pending item detection (unanswered messages, emails)
- [ ] Life balance pattern detection
- [ ] Relationship drift alerts
- [ ] Configurable pop-up cadence
- [ ] Browser-side proactive insights

---

## Phase 5 — External Data

- [x] Web content via Chrome extension (primary path)
- [ ] Amazon order history
- [ ] Apple Health / Strava
- [ ] Research-topic web scraper

---

## Ongoing

- Keep [status.md](status.md) current after major sessions
- Add eval suites before shipping new modules (see [testing.md](testing.md))
- Keep [architecture.md](architecture.md) aligned with code
- Log non-obvious choices in [decisions.md](decisions.md)
