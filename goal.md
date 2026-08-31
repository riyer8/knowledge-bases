# Context — Project Goal

> An AI that remembers what you've read and understands what you're looking at right now.

## Status

| Milestone | Status |
|---|---|
| Docs restructure (README + `docs/`) | Done |
| Chrome extension MVP | Done |
| Native host auto-start | Done |
| OpenAI auto-detection | Done |
| Knowledge graph | Done |
| Unified chat + saved library UX | Done |

## What Context Does

1. **Reads the page you're on** — title, structure, selection, visible text
2. **Unified chat** — explain, connect, quiz, explore via natural language (no mode tabs)
3. **Explicit save** — save pages only when you choose; save individual quotes from highlights
4. **Saved library** — browse saved pages with summary, chat history, quotes, and per-page memory clear
5. **Sparkles explore** — AI-suggested things to explore next
6. **Knowledge graph** — visual map of saved pages, quotes, and concepts

## Quick Start

```bash
cp .env.example .env          # add OPENAI_API_KEY
python3 -m pip install -r requirements.txt
bash chrome-extension/install-native-host.sh YOUR_EXTENSION_ID
python3 main.py               # or click the extension (auto-starts)
```

Load `chrome-extension/` in `chrome://extensions`, open any page, click Context.

## Architecture

```text
Chrome Extension (eyes + UI)
  Chat | Saved | Graph
        │ page context, questions, explicit saves
        ▼
Python Backend (localhost:8765)
  ├── library (~/.kb/library/) — saved pages, quotes, chat history
  ├── concept graph (~/.kb/graph/concepts.json)
  ├── semantic memory (~/.kb/index/)
  └── LLM (OpenAI auto / Ollama / Anthropic)
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/ask` | Unified chat with page context (streamable) |
| `POST` | `/library/save-page` | Explicitly save a page + summary |
| `GET` | `/library/pages` | List saved pages |
| `GET` | `/library/pages/{id}` | Saved page detail + chat + quotes |
| `DELETE` | `/library/pages/{id}` | Clear memory for one page |
| `POST` | `/library/quotes` | Save an individual quote |
| `GET` | `/library/quotes` | List quotes |
| `POST` | `/library/explore` | Sparkles suggestions |
| `GET` | `/library/graph` | Graph nodes + edges for visualization |
| `POST` | `/library/clear` | Wipe all stored data |
| `GET` | `/concepts` | List or search concept graph |
| `GET` | `/connections` | Related concepts + prior reading |

## LLM Configuration

Set `KB_LLM_PROVIDER=auto` (default) — uses OpenAI when `OPENAI_API_KEY` is set, otherwise Ollama.

## Data Locations

All runtime data lives under `~/.kb/`:

- `library/` — saved pages, quotes, per-page chat history
- `graph/` — concept graph
- `index/` — semantic memory embeddings
- `pages/` — legacy ephemeral page context (not auto-used by extension)

Use **Clear all data** in the extension footer or `POST /library/clear` to reset.
