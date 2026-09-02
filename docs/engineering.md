# Engineering Workflow

This document supplements `CLAUDE.md` (constitution) and `init.md` (session protocol).
Read both before making changes.

## Session start checklist

1. Read `CLAUDE.md`
2. Read [status.md](status.md) — where we left off
3. Read [agents.md](agents.md) — confirm your ownership boundary
4. Read relevant [specs/](specs/) for modules you will touch
5. Scan [decisions.md](decisions.md) for constraints
6. Check [architecture.md](architecture.md) dependency graph for blast radius
7. Write a scope declaration before editing (see `init.md`)

## Session end checklist

1. Update [status.md](status.md) with what happened and next action
2. Add to [decisions.md](decisions.md) if you made a non-obvious architectural choice
3. Run `pytest tests/`
4. Update [roadmap.md](roadmap.md) checkboxes if you completed a milestone

## Memory mutation rules

| Storage | Rule | Writer |
|---|---|---|
| `~/.kb/events/raw/` | append-only | ingestion |
| `~/.kb/events/clean/` | append-only | privacy |
| `~/.kb/index/` | mutable | memory |
| `~/.kb/graph/` | mutable | memory |
| `~/.kb/library/` | mutable | memory |
| `~/.kb/hashes/map.json` | mutable | privacy |

Never store raw screenshots, plaintext names, or PII in logs.

## Trace log template

Optional for complex sessions. Save as `docs/traces/TASK-NNN-YYYY-MM-DD.md`:

```markdown
# Trace: TASK-NNN — YYYY-MM-DD

## Reads
- [timestamp] Read status.md — noted: ...

## Implementation
- [timestamp] Created/modified ...

## Tests
- [timestamp] pytest tests/ — N passing

## Open items
- ...
```

## Postmortem template

When something fails in a way that could recur:

```markdown
# PM-NNN: Short title

- **Date**: YYYY-MM-DD
- **Severity**: low | medium | high

## What happened
## Root cause
## Resolution
## Harness changes (must have at least one)
- [ ] Updated spec in docs/specs/
- [ ] Added eval case
- [ ] Updated CLAUDE.md or init.md
```

## Specs index

| Spec | Purpose |
|---|---|
| [privacy-pipeline.md](specs/privacy-pipeline.md) | Mandatory privacy gate |
| [event-schema.md](specs/event-schema.md) | Raw/clean event contract |
| [name-anonymization.md](specs/name-anonymization.md) | Hash → display mapping |
| [buckets.md](specs/buckets.md) | Life bucket taxonomy (Phase 3) |

## Interface contract rule

When creating cross-module functions, document the contract in [agents.md](agents.md)
under the owning agent. Format: `function(input) -> output | raises Error`.

If you change an existing contract, update all callers in the same session or log the
dependency in [status.md](status.md) blockers.
