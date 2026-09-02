# Project Status

_Last updated: 2026-09-02_

## Start here tomorrow

1. Read [constitution.md](constitution.md) — rules and doc index
2. Read this file — current phase and module health
3. Pick work from [roadmap.md](roadmap.md) (next: desktop `/ask` chat)
4. Follow [init.md](../init.md) for session protocol

Quick health check:

```bash
pytest tests/ -q
curl http://127.0.0.1:8765/health
```

## Current phase

**Extension MVP shipped. Docs and repo structure consolidated for scale.**

The Python backend on `localhost:8765` serves Chrome extension and macOS app. Storage is
unified at `~/.kb/`. Documentation lives entirely in `docs/`.

## Recently completed

- Full docs consolidation: constitution, configuration, storage, engineering workflow
- Removed legacy harness folders (`STATE/`, `TASKS/`, `SPECS/`, `AGENTS/`, `EVALS/`, etc.)
- Privacy eval harness (22 cases in `tests/test_privacy_eval_cases.py`)
- macOS Library panel wired to `/library/*`
- Launcher auto-start for Chrome extension (`scripts/install-launcher.mjs`)
- Swift build fixes (`Combine` import, About panel credits)

## Next priorities

1. Desktop chat on `POST /ask` with streaming (parity with extension)
2. Proactive "you've read this before" popups using `/connections`
3. Retrieval latency benchmarks (see [testing.md](testing.md))

## Active decisions

| Decision | Summary |
|---|---|
| Local-first at `~/.kb/` | No cloud sync; privacy is the product |
| Multi-provider LLM | `auto` prefers OpenAI when key set, else Ollama |
| Extension is a client | Backend owns memory; clients are thin |
| Launcher over native messaging | HTTP launcher on :8798 starts backend on :8765 |
| Docs in `docs/` only | `init.md` at root for session protocol; rules in `docs/constitution.md` |

Full rationale: [decisions.md](decisions.md)

## Module health

| Module | Status | Notes |
|---|---|---|
| `core/config.py` | done | |
| `core/privacy/` | done | eval harness in tests |
| `core/ingestion/` | done | |
| `core/memory/` | done | |
| `core/retrieval/` | done | latency benchmarks pending |
| `core/integrations/` | done | GCal, Gmail read-only |
| `core/proactive/` | partial | engine done; browser UI pending |
| `core/library_service.py` | done | |
| `chrome-extension/` | done | |
| `DesktopApp/` | partial | library done; `/ask` chat pending |

## Known issues

None blocking.

## Blockers

None.
