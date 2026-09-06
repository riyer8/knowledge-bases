# Engineering Constitution

_Last updated: 2026-09-06_

**Read this at the start of every session** (with [status.md](status.md) and [init.md](../init.md)).

This is the engineering constitution for **Context** — a privacy-first personal knowledge
system for macOS. Chrome extension + Context.app share a Python backend (`localhost:8765`)
and storage (`~/.kb/`). AI agents and human contributors must follow these rules.

---

## Non-negotiables (quick reference)

1. **Privacy pipeline** — all data through `core/privacy/` before storage
2. **No PII in logs** — never log names, emails, or raw screenshot content
3. **Local-first** — no cloud sync; read-only external integrations only
4. **LLM routing** — use `core/llm_providers.py` / `core/llm_service.py` only
5. **Config paths** — use `core/config.py`; no hardcoded paths or model names
6. **Tests** — `pytest tests/` must pass before marking work complete

---

## Where to look

| Need | Doc |
|---|---|
| Current state | [status.md](status.md) |
| What to build next | [roadmap.md](roadmap.md) |
| Extension pitfalls + next sprints | [extension-pitfalls-and-next.md](extension-pitfalls-and-next.md) |
| Architecture | [architecture.md](architecture.md) |
| API endpoints | [api.md](api.md) |
| Module ownership | [agents.md](agents.md) |
| Specs (events, privacy, buckets) | [specs/](specs/) |
| Env vars | [configuration.md](configuration.md) |
| Storage layout | [storage.md](storage.md) |
| Decisions log | [decisions.md](decisions.md) |
| Setup | [getting-started.md](getting-started.md) |
| Session workflow | [engineering.md](engineering.md) |

Cross-module changes → [decisions.md](decisions.md). Session protocol → [init.md](../init.md).

---

## Project purpose

Capture life across multiple signals (screen, calendar, messages, web reading), anonymize it,
index it, and make it queryable via chat. The goal is a smarter, more pervasive Obsidian — one
that builds your knowledge graph passively, not manually.

---

## Architecture rules

| Rule | Detail |
|---|---|
| No duplicate services | Check [status.md](status.md) module health before adding code |
| Event contract | Changing `core/ingestion/` requires updating [specs/event-schema.md](specs/event-schema.md) |
| Privacy gate | All data must pass through `core/privacy/` before storage — no bypasses |
| Deterministic pipelines | Process events in bounded steps; no infinite autonomous loops |
| Local-first | Data stays on device unless user configures a read-only integration |
| One schema per data type | Shared contracts live in [specs/](specs/) |

---

## Privacy rules (non-negotiable)

1. **Never store raw screenshots.** Extract text/metadata, then delete the image unless explicitly flagged to keep.
2. **Never store unhashed personal names.** Hash at ingestion; UI renders via hash→display map. See [specs/name-anonymization.md](specs/name-anonymization.md).
3. **Auto-pause on sensitive content.** Password fields, banking URLs, credential forms → pause capture. See [specs/privacy-pipeline.md](specs/privacy-pipeline.md).
4. **Sensitive sites list** lives only in `core/privacy/sensitive_sites.py`.
5. **Never log PII** to stdout, log files, or traces.

---

## Coding standards

### Python

- Python 3.11+, typed where non-trivial
- No global mutable state
- No `import *`
- No bare `except:` clauses
- All new modules with side effects need tests in `tests/`
- Paths via `core/config.py` — never hardcoded
- LLM calls via `core/llm_providers.py` / `core/llm_service.py` — never direct API calls

### Swift

- SwiftUI for UI (AppKit only when unavoidable)
- Follow patterns in `DesktopApp/` (window controllers, `BackendService`, stores)
- New views need `import Combine` when using `@Published` / `ObservableObject`

### General

- Tests must pass before marking work complete (`pytest tests/`)
- No auto-committing without user approval
- No autonomous agents taking actions without a human-readable audit log

---

## Ownership boundaries

Full agent specs: [agents.md](agents.md).

| Module | Owner |
|---|---|
| `core/ingestion/` | ingestion-agent |
| `core/privacy/` | privacy-agent |
| `core/memory/`, `library_service`, `page_context_service`, `wiki_service` | memory-agent |
| `core/retrieval/` | retrieval-agent |
| `core/integrations/` | integration-agent |
| `core/proactive/` | proactive-agent |
| `DesktopApp/`, `chrome-extension/`, `web/` | frontend-agent |
| `tests/` | eval-agent |
| `core/config.py`, `env_settings.py`, `http/`, `main.py`, `frontend_backend.py`, `scripts/` | infra-agent |

Cross-module changes → new entry in [decisions.md](decisions.md).

---

## Task and status rules

- Track work in [roadmap.md](roadmap.md) and [status.md](status.md)
- Define success criteria before starting
- Do not start work blocked by [status.md](status.md) blockers
- Break multi-module work into milestones touching ≤2 modules each

---

## Testing requirements

| Area | Requirement |
|---|---|
| New side-effecting functions | Unit test in `tests/` |
| Privacy pipeline | Detection accuracy, false positives, reversibility; run `tests/test_privacy_eval_cases.py` |
| Retrieval | Latency gate: `tests/test_retrieval_latency.py` (p95 < 2s) — see [testing.md](testing.md) |
| Shipping | A broken privacy filter is worse than a missing feature |

---

## Forbidden patterns

- Storing plaintext names, emails, or phone numbers outside the hash map
- Writing to disk outside paths defined in `core/config.py`
- Business logic in `frontend_backend.py` (routing only)
- Hardcoded model names or file paths
- Weakening privacy detection without updating eval fixtures

---

## Memory mutation rules

| Location | Rule | Writer |
|---|---|---|
| `~/.kb/events/raw/` | append-only, short TTL | ingestion |
| `~/.kb/events/clean/` | append-only | ingestion (after privacy) |
| `~/.kb/events/paused.log` | append-only | privacy |
| `~/.kb/library/` | mutable | memory |
| `~/.kb/pages/` | mutable | memory |
| `~/.kb/wiki/` | mutable | memory (`wiki_service`) |
| `~/.kb/index/` | mutable | memory |
| `~/.kb/graph/` | mutable | memory |
| `~/.kb/relationships/` | mutable | memory |
| `~/.kb/hashes/map.json` | mutable | privacy |
| `~/.kb/hashes/salt` | write-once | privacy (`hasher` on first hash) |
| `~/.kb/auth/` | mutable | integrations |
| `~/.kb/buckets/` | mutable | memory |

Details: [storage.md](storage.md)

---

## Dependency graph

```text
Clients (extension, web/, DesktopApp)
        → frontend_backend.py + core/http/*
        → retrieval | proactive | ingestion | library | wiki | page_context
        → privacy (mandatory for ingestion)
        → memory (+ relationships, buckets)
        → llm_providers
```

Before changing a module: identify consumers, dependencies, and blast radius.
Full architecture: [architecture.md](architecture.md).
