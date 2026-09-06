# Roadmap

_Last updated: 2026-09-06_

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

## Phase 5 — LLM Wiki (Karpathy-style knowledge base)

Inspired by [Karpathy's knowledge base workflow](https://x.com/karpathy/status/2039805659525644595).

- [x] Raw source ingest (`~/.kb/wiki/raw/`)
- [x] LLM incremental compile into linked articles (`~/.kb/wiki/articles/`)
- [x] Auto-maintained `index.md` + manifest
- [x] Wiki health check (gaps, inconsistencies, article ideas)
- [x] Full-text search (`GET /wiki/search`)
- [x] Local web UI (`http://127.0.0.1:8765/app/`)
- [x] Chrome extension Wiki tab + add-to-wiki from saved pages
- [x] Desktop Wiki panel (articles, compile, ask)
- [ ] Obsidian vault sync (open `~/.kb/wiki/` as vault — manual for now)
- [ ] Marp slide output generation
- [ ] Synthetic data + finetuning experiments

---

## Ongoing

- [x] Keep [status.md](status.md) current after major sessions
- [x] Add eval suites before shipping new modules (see [testing.md](testing.md))
- [x] Retrieval latency benchmarks (`tests/test_retrieval_latency.py`, p95 < 2s)
- Keep [architecture.md](architecture.md) aligned with code
- Log non-obvious choices in [decisions.md](decisions.md)

---

## Reading-first (current)

Primary loop: highlight on the page → notes in the side panel → Copy JSON onto a personal site. Spec: [notes-export.md](specs/notes-export.md).

Pending pitfalls, Desktop integration gap, and sprint order: [extension-pitfalls-and-next.md](extension-pitfalls-and-next.md).

- [x] Notes editor is the export source of truth
- [x] Bookshelf JS object (`:::quote` fences) matches the editor
- [x] Persist `dateAdded` on first save
- [x] Dashboard + Saved show the same notes document
- [ ] Extension trust (draft-aware paint, draft write mutex, reinject) — Sprint A
- [ ] Library-wide bookshelf export
- [ ] Saved list filters
- [ ] Desktop library notes parity

Life and Wiki stay [archived](archived.md).
