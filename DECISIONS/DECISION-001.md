# DECISION-001: Local-first storage at ~/.kb/

- **Date**: 2026-05-19
- **Status**: accepted
- **Decided by**: human

## Context
The system captures sensitive personal data: messages, screen content, calendar events,
health data, relationship dynamics. We need to decide where this data lives.

## Decision
All data is stored locally at `~/.kb/`. Nothing is synced to external servers.
External integrations (GCal, Gmail, Slack) are read-only sources — we pull from them,
we never push to them or store data on them.

## Rationale
Privacy is the core product value. Storing data in the cloud would:
- Require trusting a third party with highly sensitive personal data
- Create regulatory/legal exposure
- Undermine user trust as the primary differentiator
- Add latency and complexity

Local storage means: if the machine is off, nothing leaks. Full stop.

## Alternatives Considered
- **Cloud storage (encrypted)** — rejected: still requires trusting key management, adds complexity
- **iCloud sync** — rejected: scope creep, adds complexity, out of scope for Phase 1

## Consequences
- Backups are the user's responsibility
- Multi-device sync is out of scope (intentionally)
- Storage will grow over time — user should be able to set retention policies (future task)
