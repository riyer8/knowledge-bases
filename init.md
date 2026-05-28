# init.md — Session Initialization Protocol

Every Claude session in this repository must follow this protocol in full.
Do not skip steps. Do not reorder steps. The protocol exists because context loss
between sessions is the primary failure mode of AI-assisted engineering.

---

## Phase 1: Orient (Read Before Anything Else)

Execute these reads in order. Do not begin implementation until all are complete.

### Step 1 — Engineering Constitution
```
Read: CLAUDE.md
```
Internalize the rules. If anything in your task would violate CLAUDE.md, stop and flag it.

### Step 2 — Current State
```
Read: STATE/current.md
```
Understand exactly where the last session left off. What was completed, what is next,
what active decisions are in play.

### Step 3 — Active Tasks
```
Read: STATE/active_tasks.md
```
Confirm which task you're picking up. If unclear, do not guess — surface the ambiguity.

### Step 4 — Blockers
```
Read: STATE/blockers.md
```
If any blocker affects your task, do not proceed past this point without resolving it or
documenting why it doesn't apply.

### Step 5 — Known Issues
```
Read: STATE/known_issues.md
```
Check for any open issues in the modules you will touch.

### Step 6 — Owned Agent Spec
```
Read: AGENTS/<your-agent>.md
```
Confirm your ownership boundaries, forbidden actions, and required tests for this session.

### Step 7 — Relevant Specs
```
Read: SPECS/<relevant>.md
```
Read every spec that describes something you will build, modify, or call.
If no spec exists for what you're about to build, write one first.

### Step 8 — Relevant Decisions
```
Read: DECISIONS/
```
Scan for any decision that touches your module or task. Decisions explain *why* things
are the way they are — violating them without a new DECISION file is not allowed.

### Step 9 — Dependency Graph Check
```
Read: ARCHITECTURE.md (Dependency Graph section)
```
Before touching any module, answer:
- What does this module depend on? (its dependencies)
- What depends on this module? (its consumers)
- What is the blast radius if I change the interface?

If a change affects a consumer you don't own, coordinate via a new TASK before proceeding.

---

## Phase 2: Declare Scope (Before First Edit)

Before making any file change, write a scope declaration. This is the last step before
implementation. Format:

```
## Session Scope Declaration
- Task: TASK-NNN
- Agent role: <agent-name>
- Files I will modify: [explicit list]
- Files I will read but not modify: [list]
- Interfaces I will change: [list, or "none"]
- Interfaces I will call: [list]
- Tests I must pass before done: [list]
- State files I will update at end: [list]
```

Do not touch any file not in your declared scope without re-declaring.
If you discover mid-session that scope must expand, pause and declare the expansion.

---

## Phase 3: Implementation

### Execution Trace Logging

Every non-trivial implementation session must write a trace log to `TRACES/`.

Name format: `TRACES/TASK-NNN-YYYY-MM-DD.md`

Trace log must record (in real time, not reconstructed at the end):

```markdown
# Trace: TASK-NNN — YYYY-MM-DD

## Reads
- [timestamp] Read CLAUDE.md — OK
- [timestamp] Read STATE/current.md — noted: privacy module not started
- ...

## Decisions Made
- [timestamp] Chose spaCy over regex for NER because: [reason]
- [timestamp] Split hasher.py from detector.py because: [reason]

## Implementation Steps
- [timestamp] Created core/privacy/__init__.py
- [timestamp] Created core/privacy/detector.py — password detection logic
- [timestamp] Ran tests/test_privacy.py — 3 passing, 1 failing (phone regex)
- [timestamp] Fixed phone regex — all 4 passing

## Failures and Recoveries
- [timestamp] FAILURE: spaCy model not found on first import
  → Root cause: model not in requirements.txt
  → Fix: added en_core_web_sm to requirements.txt, re-ran
  → Prevention: add model download to setup instructions

## Interface Changes
- [timestamp] Added pipeline.process(event) -> CleanEvent to core/privacy/pipeline.py
  → Contract: input is RawEvent, output is CleanEvent, raises PrivacyError on pause trigger

## Tests Run
- [timestamp] tests/test_privacy.py — 4/4 passing
- [timestamp] EVALS/privacy/ — 18/20 passing (2 edge cases logged to known_issues)
```

### Interface Contract Rules

When you create or modify a function that crosses module boundaries:

1. The contract must be written in the owning AGENTS/ file under "Interfaces"
2. Format: `function_name(input_type) -> output_type | raises ExceptionType`
3. If you change an existing contract, you must:
   - Update the AGENTS/ file
   - Update every caller in the same session, or
   - Create a TASK for the caller's owner to update, and add it as a blocker

### Memory Mutation Rules

These rules govern what can be written where. Violations are bugs.

| Storage Location | Rule | Who Can Write |
|---|---|---|
| `~/.kb/events/raw/` | append-only, short TTL | ingestion-agent only |
| `~/.kb/events/clean/` | append-only, permanent | privacy-agent only |
| `~/.kb/events/paused.log` | append-only | privacy-agent only |
| `~/.kb/index/` | mutable, versioned | memory-agent only |
| `~/.kb/graph/` | mutable, versioned | memory-agent only |
| `~/.kb/hashes/map.json` | mutable | privacy-agent only |
| `~/.kb/hashes/salt` | write-once, immutable | infra-agent (first run only) |
| `~/.kb/auth/` | mutable | integration-agent only |
| `~/.kb/buckets/` | mutable | memory-agent only |
| `STATE/*.md` | mutable | any agent (end of session) |
| `TASKS/*.md` | mutable | any agent (status updates only) |

**Append-only means:** never delete, never overwrite. New entries only.
**Write-once means:** written at install time, never touched again.
**Mutable means:** can be updated, but changes must be logged in the trace.

### Dependency Graph

```
                    ┌─────────────┐
                    │  DesktopApp │
                    └──────┬──────┘
                           │ HTTP
                    ┌──────▼──────┐
                    │  frontend_  │
                    │  backend.py │
                    └──┬───┬───┬──┘
                       │   │   │
           ┌───────────┘   │   └────────────┐
           │               │                │
    ┌──────▼──────┐  ┌─────▼──────┐  ┌─────▼──────┐
    │  retrieval  │  │  proactive  │  │  ingestion  │
    └──────┬──────┘  └─────┬──────┘  └─────┬──────┘
           │               │                │
           └───────┐        │         ┌─────▼──────┐
                   │        │         │   privacy   │
           ┌───────▼────────▼─────────▼──────┐
           │              memory              │
           └──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  llm_service│
                    └─────────────┘
                           │
                   Ollama / Claude API
```

**Reading the graph:**
- Arrows point from consumer → dependency
- Changing an interface in `memory` affects: retrieval, proactive, ingestion (via privacy)
- Changing `llm_service` affects: memory, retrieval, proactive
- `privacy` is a strict dependency of ingestion — ingestion cannot ship without it
- `DesktopApp` depends only on the HTTP API surface, not on internal modules

**Rule:** Before changing a module, read every node that points to it. Notify their owners.

---

## Phase 4: Session Close (Required)

Do not end a session without completing all of these.

### Step 1 — Update Task Status
In `TASKS/TASK-NNN.md`, update the `Status` field and check off completed requirements.

### Step 2 — Update STATE/active_tasks.md
Move completed tasks to the completed section. Add any newly queued tasks.

### Step 3 — Update STATE/current.md
Write a clear "what just happened" and "next action" so the next session can orient
in under 2 minutes. Be specific — not "worked on privacy" but "implemented
detector.py and hasher.py, pipeline.py still needs sensitivity scorer".

### Step 4 — Log New Issues
Any bugs found but not fixed, edge cases deferred, or degraded behavior → `STATE/known_issues.md`.

### Step 5 — Log New Blockers
Anything that blocks forward progress → `STATE/blockers.md`.

### Step 6 — Log New Decisions
If you made a non-obvious architectural choice → new file in `DECISIONS/`.

### Step 7 — Finalize Trace Log
Complete the trace log in `TRACES/`. Mark any open items.

### Step 8 — Postmortem Check
Ask: did anything fail in a way that could recur?
If yes → write a postmortem (see below).

---

## Postmortem Protocol

### When to Write One

Write a postmortem any time:
- A session failed to make meaningful progress toward its task
- A bug was introduced and found (even if fixed in the same session)
- A wrong assumption was baked in and had to be unwound
- An interface change broke a caller unexpectedly
- STATE/ was out of date and caused wasted work at session start
- A spec was missing and had to be written mid-implementation

"Institutional memory failure" = the harness did not contain information that would have
prevented the problem. The fix is always a harness update, not just fixing the code.

### Postmortem Format

File: `POSTMORTEMS/PM-NNN-short-title.md`

```markdown
# PM-NNN: Short description of what went wrong

- **Date**: YYYY-MM-DD
- **Task affected**: TASK-NNN
- **Severity**: low | medium | high
- **Type**: implementation_failure | state_loss | bad_assumption | interface_break | missing_spec

## What Happened
Timeline of what went wrong. Be specific.

## Root Cause
The actual underlying reason, not the symptom.

## Impact
What had to be redone, what risk was introduced, what was shipped incorrectly.

## Resolution
What was done to fix it this session.

## Harness Changes
What was added/updated in the harness to prevent recurrence:
- [ ] Updated SPEC: ...
- [ ] Added eval: ...
- [ ] Updated AGENT spec: ...
- [ ] Added to CLAUDE.md: ...
- [ ] New DECISION file: ...

## Lessons
One or two sentences for future sessions.
```

### The Key Rule

Every postmortem must result in at least one harness change.
A postmortem with no harness changes is just a complaint — it doesn't prevent recurrence.

---

## Quick Reference Checklist

```
SESSION START
[ ] Read CLAUDE.md
[ ] Read STATE/current.md
[ ] Read STATE/active_tasks.md
[ ] Read STATE/blockers.md
[ ] Read STATE/known_issues.md
[ ] Read AGENTS/<owned-agent>.md
[ ] Read relevant SPECS/
[ ] Scan relevant DECISIONS/
[ ] Check dependency graph for blast radius
[ ] Write scope declaration

DURING IMPLEMENTATION
[ ] Write trace log to TRACES/ (real time)
[ ] Log interface contracts when creating cross-module functions
[ ] Respect memory mutation rules
[ ] Run required tests before marking anything done

SESSION END
[ ] Update TASKS/TASK-NNN.md status
[ ] Update STATE/active_tasks.md
[ ] Update STATE/current.md (what happened + next action)
[ ] Log issues → STATE/known_issues.md
[ ] Log blockers → STATE/blockers.md
[ ] Log decisions → DECISIONS/ (if applicable)
[ ] Finalize TRACES/TASK-NNN-YYYY-MM-DD.md
[ ] Postmortem if needed → POSTMORTEMS/
```
