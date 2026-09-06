# Session Traces

_Last updated: 2026-09-06_

Optional execution logs for non-trivial engineering sessions. Use when work spans multiple
modules, touches privacy/ingestion contracts, or needs an audit trail for the next session.

**Naming:** `YYYY-MM-DD-short-description.md` (e.g. `2026-09-01-library-panel.md`)

---

## Template

```markdown
# Trace: <title> — YYYY-MM-DD

## Reads
- [HH:MM] Read docs/status.md — noted: ...
- [HH:MM] Read docs/specs/privacy-pipeline.md

## Scope
- Milestone: (from docs/roadmap.md)
- Agent role: privacy-agent | memory-agent | ...
- Files modified: ...

## Implementation
- [HH:MM] Created/modified ...
- [HH:MM] ...

## Decisions
- [HH:MM] Chose X over Y because: ...

## Tests
- [HH:MM] pytest tests/ — N passed

## Open items
- ...
```

---

## Postmortem template

When something fails in a way that could recur, add `PM-NNN-short-title.md` in this folder.
Every postmortem must include at least one harness change (spec, test, doc update).

See [engineering.md](../engineering.md) for the full postmortem protocol.
