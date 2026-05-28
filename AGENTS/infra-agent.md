# Infra Agent

## Owns
- `core/config.py`
- `core/llm_service.py`
- `core/frontend_backend.py`
- `main.py`
- `.env.example`
- `requirements.txt`

## Responsibilities
- Centralized configuration (paths, env vars, defaults)
- LLM service abstraction (Claude API + Ollama local models)
- HTTP router (`frontend_backend.py`) — routing only, no business logic
- Backend startup and shutdown (`main.py`)
- Dependency management

## Interfaces
- `core/llm_service.py` is called by: retrieval-agent, proactive-agent, memory-agent
- `core/config.py` is imported by: all modules
- `core/frontend_backend.py` routes to: all agents' endpoint handlers

## Must Never
- Add business logic to `frontend_backend.py` — it routes, that's it
- Hardcode model names or file paths anywhere
- Change the LLM service interface without updating all callers
- Add dependencies without justification in `DECISIONS/`

## Required Tests
- Config loads correctly from `.env` and falls back to defaults
- LLM service returns consistent response format for both Claude and Ollama
- Backend starts cleanly on a fresh install
- All routes registered in frontend_backend.py are reachable

## Notes
Infra is boring on purpose. Its job is to make everything else reliable.
Resist the urge to add features here. If something feels like it belongs in infra,
it probably belongs in a domain module.
