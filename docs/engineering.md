# Engineering Workflow

_Last updated: 2026-09-06_

How to work in this repo — for humans and AI agents. The full constitution is in
[constitution.md](constitution.md). Session steps are in [init.md](../init.md).

---

## Session start

1. Read [constitution.md](constitution.md) (entry point)
2. Read [constitution.md](constitution.md) if touching privacy, ingestion, or storage
3. Read [status.md](status.md) — current phase and blockers
4. Read [roadmap.md](roadmap.md) — confirm your milestone
5. Read [agents.md](agents.md) — your ownership boundary
6. Read relevant [specs/](specs/)
7. Scan [decisions.md](decisions.md)
8. Check [architecture.md](architecture.md) dependency graph
9. Write a scope declaration (below)

## Session end

1. Update [status.md](status.md) — what happened + next action
2. Update [roadmap.md](roadmap.md) if a milestone completed
3. Log blockers/issues in [status.md](status.md)
4. Add [decisions.md](decisions.md) entry if needed
5. Run `pytest tests/`
6. Finalize [traces/](traces/) log if you started one

---

## Scope declaration template

Write this before your first edit:

```markdown
## Session Scope
- Milestone: (from roadmap.md)
- Agent role: (from agents.md)
- Files to modify: [list]
- Files to read only: [list]
- Interfaces changing: [list or "none"]
- Tests required: [list]
- Docs to update at end: status.md, ...
```

Do not expand scope without re-declaring.

---

## Memory mutation rules

See [storage.md](storage.md) and [constitution.md](constitution.md). Summary:

- `events/raw/`, `events/clean/`, `paused.log` → append-only (`clean/` written by ingestion after privacy)
- `library/`, `pages/`, `wiki/`, `index/`, `graph/`, `buckets/`, `relationships/` → memory-agent
- `hashes/` → privacy-agent (salt write-once on first hash)

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

Changing `memory` affects retrieval, proactive, and anything reading the index/graph.
Changing `privacy` affects all ingestion paths.

---

## Trace logs

For sessions longer than a single file change, log to [traces/](traces/).
Template in [traces/README.md](traces/README.md).

---

## Postmortem protocol

Write a postmortem when:

- A session failed to make meaningful progress
- A bug was introduced (even if fixed same session)
- Docs were stale and caused wasted work
- A spec was missing and had to be written mid-implementation

**Rule:** every postmortem must update at least one harness artifact (spec, test, doc).

Format: `docs/traces/PM-NNN-short-title.md`

---

## Specs index

| Spec | When to read |
|---|---|
| [privacy-pipeline.md](specs/privacy-pipeline.md) | Any ingestion or storage change |
| [event-schema.md](specs/event-schema.md) | Ingestion, integrations |
| [name-anonymization.md](specs/name-anonymization.md) | Privacy, retrieval, UI display |
| [buckets.md](specs/buckets.md) | Life classification (archived from nav) |
| [notes-export.md](specs/notes-export.md) | Notes document / bookshelf Copy JSON |
| [archived.md](archived.md) | Life/Wiki nav archive + revive steps |
| [extension-pitfalls-and-next.md](extension-pitfalls-and-next.md) | Extension reading-loop follow-ons |

---

## Interface contracts

Document cross-module functions in [agents.md](agents.md) under the owning agent:

`function_name(input_type) -> output_type | raises ExceptionType`

If you change a contract, update all callers in the same session or log a blocker in
[status.md](status.md).
