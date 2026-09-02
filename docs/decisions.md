# Architectural Decisions

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

## DECISION-004: Docs consolidated under `docs/`

- **Date**: 2026-09-01
- **Status**: accepted

Product and engineering documentation lives in `docs/`. Root keeps only `CLAUDE.md`
(constitution) and `init.md` (agent session protocol).

**Rationale:** Single readable source of truth; avoids scattered STATE/SPECS/TASKS folders.

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
