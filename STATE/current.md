# Current State

_Updated: 2026-08-30_

## What Just Happened

- Chrome extension MVP complete: unified chat, saved library, quotes, concept graph
- Docs consolidated into `docs/` (architecture, API, roadmap, project structure)
- Python backend serves both Chrome extension and macOS desktop app on `localhost:8765`

## Current Phase

**Extension MVP shipped. Desktop app integration next.**

The shared backend and `~/.kb/` storage are in place. The macOS app exists but does not yet
surface the extension's saved library (`/library/*`) or page-context chat (`/ask`).

## Next Action

1. Wire `DesktopApp/` to `/library/*` endpoints (saved pages, quotes, graph)
2. Unify desktop chat on `POST /ask`
3. Proactive "you've read this before" using `/connections`

## Active Decisions

- Local-first storage at `~/.kb/`
- LLM: `KB_LLM_PROVIDER=auto` (OpenAI when key set, else Ollama)
- Chrome extension is a client, not the database — backend owns memory
- Single repo for all clients (no separate backend repo)

## Quick Links

- [goal.md](../goal.md) — project status
- [docs/architecture.md](../docs/architecture.md) — system design
- [docs/getting-started.md](../docs/getting-started.md) — run everything
