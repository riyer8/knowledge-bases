# DECISION-002: Ollama for heavy processing, Claude API for chat

- **Date**: 2026-05-19
- **Status**: accepted
- **Decided by**: human

## Context
The system needs LLM capabilities for: chunking, embedding, entity extraction, classification,
relationship detection, and chat. The user does not want to pay separately for API keys
(already paying for Claude + ChatGPT subscriptions).

## Decision
- **Local via Ollama**: all heavy background processing (embeddings, classification, entity extraction, relationship detection)
- **Claude API**: the chat interface only (highest quality needed for conversational responses)
- **All calls**: routed through `core/llm_service.py` — no direct API calls anywhere

## Rationale
- Ollama is free and runs locally — no API cost for bulk processing
- Background processing happens asynchronously, so local model latency is acceptable
- Chat is synchronous and user-facing — quality matters more than cost here
- Centralizing through llm_service.py means we can swap models without changing callers

## Alternatives Considered
- **All Ollama** — chat quality would be noticeably worse for users
- **All Claude API** — cost would grow with usage, against user's preference
- **All ChatGPT** — same cost concern; Claude is preferred for the chat UX

## Consequences
- Need Ollama installed locally (added to setup instructions)
- `core/llm_service.py` needs to support two backends cleanly
- If user wants to go all-local in the future, only the chat endpoint needs to change
