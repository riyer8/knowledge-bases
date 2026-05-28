# Current State

_Updated: 2026-05-19_

## What Just Happened
Built the repo harness from scratch:
- CLAUDE.md (engineering constitution)
- ARCHITECTURE.md (full system design)
- ROADMAP.md (5-phase build plan)
- AGENTS/ (8 agent specs)
- STATE/, TASKS/, SPECS/, DECISIONS/, EVALS/ scaffolding

## Current Phase
**Phase 1 — Harden the Foundation**

The repo was empty before this session. No production code exists yet.
The harness is now in place. Next session should begin building `core/`.

## Next Action
Start Phase 1 implementation:
1. Create `core/config.py` — centralized config (infra-agent)
2. Create `core/privacy/` module (privacy-agent) — this is the most critical first module
3. Create `core/ingestion/` (ingestion-agent) — wired to privacy

Do not start integrations or the proactive bot until privacy + indexing are solid.

## Active Decisions
- LLM strategy: Ollama for heavy processing, Claude API for chat
- Storage: local-only at `~/.kb/`
- Name anonymization: SHA-256 + per-install salt
- No raw screenshots stored after text extraction
