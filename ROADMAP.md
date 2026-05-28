# Roadmap

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked

---

## Phase 1 — Harden the Foundation
*Make what exists trustworthy before expanding.*

- [ ] Set up repo harness (CLAUDE.md, AGENTS/, STATE/, SPECS/, TASKS/, EVALS/)
- [ ] Create `core/config.py` — centralized path + env config
- [ ] Create `core/privacy/` module
  - [ ] Password field / credential form detection
  - [ ] Banking + sensitive site URL detection
  - [ ] Auto-pause signal to screen capture
  - [ ] Name detection and hashing pipeline
  - [ ] Hash → display name reverse rendering
- [ ] Improve screen capture
  - [ ] Privacy gate integration
  - [ ] Importance flagging (user can mark "this matters")
  - [ ] Menu bar controls: start / stop / flag
- [ ] Improve indexing
  - [ ] Chunking + embedding pipeline
  - [ ] Semantic retrieval (not just graph traversal)
- [ ] Eval harness for privacy pipeline (`EVALS/privacy/`)
- [ ] Tests for all Phase 1 modules

---

## Phase 2 — Integrations (Data In)
*More signal = smarter system.*

- [ ] Google Calendar integration
  - [ ] OAuth setup
  - [ ] Event ingestion into pipeline
  - [ ] Time-context for chat queries
- [ ] Gmail integration
  - [ ] OAuth setup
  - [ ] Thread ingestion (subject + metadata, not full body by default)
  - [ ] Pending/unanswered detection
- [ ] iMessage integration (local DB read)
- [ ] Slack integration (optional)
- [ ] Each integration feeds the same clean event pipeline

---

## Phase 3 — Buckets of Life + Relationship Profiles
*Structure what's been collected.*

- [ ] Define life bucket taxonomy (SPECS/buckets.md)
  - [ ] Health, Work, Relationships, Learning, Finances, Home, Creativity, Other
  - [ ] User-customizable, user-reorderable
- [ ] Auto-classification of events into buckets
- [ ] Tree view in frontend (filter by time, bucket, activity type)
- [ ] Relationship profiles
  - [ ] Auto-built from ingested events
  - [ ] One profile per hashed person
  - [ ] Ping notification when profile is updated
  - [ ] User can refine/edit profile
- [ ] "How I spend my time" dashboard (not just screen time — actual life signal)

---

## Phase 4 — Proactive Bot
*Shift from reactive to proactive.*

- [ ] Pending item detection (unanswered messages, emails, tasks)
- [ ] Life balance pattern detection
- [ ] Relationship drift alerts ("haven't interacted with X in 3 weeks")
- [ ] Scheduled pop-up cadence (configurable)
- [ ] Non-intrusive UI — appears, user can dismiss or engage
- [ ] Proactive insights logged so user can review later

---

## Phase 5 — Web Scraper + External Data
*Broadest surface area, do last.*

- [ ] Web content ingestion (user pastes URL or browser extension sends it)
- [ ] Amazon order history
- [ ] Fitness app integrations (Apple Health, Strava, etc.)
- [ ] Web scraper for topics the user is actively researching

---

## Ongoing (Every Phase)

- Keep `STATE/` updated after every session
- Add evals before shipping each module
- Keep `ARCHITECTURE.md` current with actual state
- Log decisions to `DECISIONS/` when making non-obvious choices
