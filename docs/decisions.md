# Architectural Decisions

_Last updated: 2026-09-06_

Record of non-obvious choices. Add a new dated section when making a cross-cutting change.

---

## DECISION-001: Local-first storage at `~/.kb/`

- **Date**: 2026-05-19
- **Status**: accepted

All data is stored locally at `~/.kb/`. Nothing is synced to external servers.
External integrations (GCal, Gmail) are read-only sources.

**Rationale:** Privacy is the core product value. Local storage means if the machine is off,
nothing leaks.

**Consequences:** Backups are the user's responsibility. Multi-device sync is out of scope.

---

## DECISION-002: Ollama for heavy processing, APIs for chat

- **Date**: 2026-05-19
- **Status**: accepted (evolved)

Originally: Ollama for background processing, Claude API for chat only.

**Current state:** `KB_LLM_PROVIDER=auto` uses OpenAI when `OPENAI_API_KEY` is set,
otherwise Ollama. Anthropic is also supported. All calls route through
`core/llm_providers.py` — no direct API calls in feature code.

**Rationale:** Centralizing LLM access allows swapping providers without changing callers.

---

## DECISION-003: HTTP launcher instead of Chrome native messaging

- **Date**: 2026-08
- **Status**: accepted

The extension calls `POST http://127.0.0.1:8798/start` (LaunchAgent) to start the backend
on port 8765. Native messaging (`install-native-host.sh`) remains as a legacy fallback.

**Rationale:** Simpler setup (no extension ID in manifest), matches apt-hunter pattern,
fewer Chrome permission issues.

---

## DECISION-004: Documentation consolidated under `docs/`

- **Date**: 2026-09-01
- **Status**: accepted

Product and engineering documentation lives in `docs/`. Root keeps only `init.md` (session protocol).

Legacy folders removed: `STATE/`, `TASKS/`, `SPECS/`, `AGENTS/`, `EVALS/`, `POSTMORTEMS/`, `TRACES/`, `inputs/`, `CLAUDE.md`.

**Rationale:** Single readable source of truth; agents read `docs/constitution.md` + `docs/status.md`.

---

## DECISION-005: Constitution in docs only

- **Date**: 2026-09-02
- **Status**: accepted

Removed root `CLAUDE.md`. All engineering rules live in `docs/constitution.md` (including the
doc index and non-negotiables quick reference formerly in CLAUDE.md).

**Rationale:** Avoid duplicate entry points; `docs/` is the single documentation tree.

---

## Template for new decisions

```markdown
## DECISION-NNN: Short title

- **Date**: YYYY-MM-DD
- **Status**: proposed | accepted | superseded

### Context
Why a decision was needed.

### Decision
What we chose.

### Rationale
Why.

### Consequences
What changes as a result.
```
