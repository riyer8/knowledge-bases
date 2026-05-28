# TASK-001: Create core/config.py

- **Status**: complete
- **Owner**: infra-agent
- **Phase**: 1
- **Created**: 2026-05-19
- **Completed**: 2026-05-27

## Goal
Create a centralized configuration module that all other modules import. This prevents
hardcoded paths and makes the system configurable via environment variables without
each module having to parse .env directly.

## Scope
- `core/config.py` (create)
- `.env.example` (create)
- `requirements.txt` (create)

## Requirements
- [ ] All storage paths derived from `KB_ROOT` env var, defaulting to `~/.kb/`
- [ ] Model names (Claude, Ollama) configurable via env vars
- [ ] Backend port configurable (default 8765)
- [ ] Sensitive site list path configurable
- [ ] Config module usable with `from core.config import config`

## Dependencies
- None (this is the first task)

## Success Criteria
- [ ] `from core.config import config` works from any module
- [ ] All paths use `config.kb_root`, never hardcoded strings
- [ ] `.env.example` documents every env var
- [ ] `tests/test_config.py` covers default values and env var overrides

## Notes
Keep this simple. It's a config module, not a framework. A dataclass or simple class
with classmethods is sufficient. No dynamic reloading needed.
