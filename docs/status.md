# Project Status

_Last updated: 2026-09-01_

## Current phase

**Chrome extension MVP shipped. macOS app wired to shared library.**

The Python backend on `localhost:8765` serves both clients. Storage is unified at `~/.kb/`.
The desktop app now surfaces the saved reading library from the extension.

## Recently completed

- Chrome extension: Quotes | Chat tabs, launcher auto-start (`scripts/install-launcher.mjs`)
- Docs consolidated into `docs/` (single source of truth)
- Privacy eval harness (`tests/test_privacy_eval_cases.py` + fixtures)
- macOS **Context** app with icon, menu bar, auto-backend on launch
- macOS library panel (`/library/pages`, `/library/quotes`)

## Next priorities

1. Desktop chat on `POST /ask` (same streaming path as extension)
2. Proactive "you've read this before" popups using `/connections`
3. Retrieval latency benchmarks (see [testing.md](testing.md))

## Active decisions

| Decision | Summary |
|---|---|
| Local-first at `~/.kb/` | No cloud sync; privacy is the product |
| Multi-provider LLM | `auto` prefers OpenAI when key set, else Ollama |
| Extension is a client | Backend owns memory; clients are thin |
| Launcher over native messaging | HTTP launcher on :8798 starts backend on :8765 |

Full rationale: [decisions.md](decisions.md)

## Module health

| Module | Status |
|---|---|
| `core/config.py` | done |
| `core/privacy/` | done |
| `core/ingestion/` | done |
| `core/memory/` | done |
| `core/retrieval/` | done |
| `core/integrations/` | done (GCal, Gmail read-only) |
| `core/proactive/` | done (engine exists; UI partial) |
| `core/library_service.py` | done |
| `chrome-extension/` | done |
| `DesktopApp/` | partial — library wired; `/ask` chat pending |

## Known issues

None blocking. See [roadmap.md](roadmap.md) for planned work.

## Blockers

None.
