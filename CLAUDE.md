# CLAUDE.md — Engineering Constitution

This file governs all agent behavior in this repository. Read it at the start of every session.
Do not proceed with any task without understanding these rules.

---

## Project Purpose

A persistent, privacy-first personal knowledge system for macOS. It captures life across multiple
signals (screen, calendar, messages, health, relationships), anonymizes it, indexes it, and makes
it queryable via chat. The goal is a smarter, more pervasive Obsidian — one that builds your
knowledge graph passively, not manually.

---

## Session Protocol

**Follow `init.md` in full at the start of every session.**

`init.md` defines the complete initialization protocol including: read order, scope declaration,
execution trace logging, dependency graph checks, interface contract rules, memory mutation rules,
session close steps, and the postmortem protocol.

Never start building without reading state. Never end a session without updating state.

---

## Architecture Rules

- **Never create a service that duplicates an existing one.** Check `docs/status.md` (module health) first.
- **Never modify `core/ingestion/` without updating the event contract** in `docs/specs/event-schema.md`.
- **Never bypass the privacy pipeline.** All data entering the system must pass through `core/privacy/` before storage.
- **Prefer deterministic pipelines over autonomous loops.** Agents should process events, not spin indefinitely.
- **Local-first.** No data leaves the machine unless the user has explicitly configured an integration.
- **One source of truth per data type.** If two modules need the same data, define a shared schema in `docs/specs/`.

---

## Privacy Rules (Non-Negotiable)

- **Never store raw screenshots.** Extract text/metadata, then delete the image unless explicitly flagged to keep.
- **Never store unhashed personal names.** All names must be hashed at ingestion. The UI layer renders them back using the hash→display mapping.
- **Auto-pause on sensitive content.** Screen capture must pause when a password field, banking URL, or credential form is detected. See `docs/specs/privacy-pipeline.md`.
- **Sensitive site list is in `core/privacy/sensitive_sites.py`.** Update it there, nowhere else.
- **Never log PII to stdout or any log file.**

---

## Coding Standards

- Python: 3.11+, typed where non-trivial, no global mutable state
- Swift: SwiftUI only (no AppKit unless unavoidable), follow existing window patterns in `DesktopApp/`
- All new Python modules must have a corresponding test file in `tests/`
- Tests must pass before a task is marked complete
- No hardcoded file paths — use environment variables with defaults defined in `core/config.py`
- No hardcoded model names — all LLM calls go through `core/llm_service.py`

---

## Ownership Boundaries

Each module is owned by one agent. Do not modify another agent's module without explicit task scope.

| Module | Owner Agent |
|---|---|
| `core/ingestion/` | ingestion-agent |
| `core/privacy/` | privacy-agent |
| `core/memory/` | memory-agent |
| `core/retrieval/` | retrieval-agent |
| `core/integrations/` | integration-agent |
| `core/proactive/` | proactive-agent |
| `DesktopApp/` | frontend-agent |
| `tests/` | eval-agent |
| `core/config.py`, `main.py` | infra-agent |

Cross-module changes require updating `docs/decisions.md` with a rationale.

---

## Task Rules

- Track work in `docs/roadmap.md` and `docs/status.md`.
- Every task must have explicit success criteria before work begins.
- Mark milestones complete by updating `docs/roadmap.md` and `docs/status.md`.
- Do not start work blocked by items in `docs/status.md` (Blockers section).
- Break tasks that would touch more than 2 modules into smaller milestones.

---

## Testing Requirements

- Every new function with side effects must have a test.
- Privacy pipeline functions require tests for: detection accuracy, false positive rate, reversibility.
- Retrieval functions require latency benchmarks (see `docs/testing.md`).
- Do not skip tests to ship faster. A broken privacy filter is worse than no feature.

---

## Forbidden Patterns

- No `import *`
- No bare `except:` clauses
- No storing plaintext names, emails, or phone numbers outside of the hash map
- No calling external LLM APIs directly — always go through `core/llm_service.py`
- No writing to disk outside of the paths defined in `core/config.py`
- No auto-committing to git without user approval
- No autonomous agents that take actions without a human-readable audit log
