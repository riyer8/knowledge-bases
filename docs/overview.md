# Context — Overview

> An AI that remembers what you've read and understands what you're looking at right now.

**Context** is a local-first personal knowledge system for macOS. A Chrome extension captures
what you read on the web; a shared Python backend indexes it; a macOS app gives you the same
memory from the desktop. Everything stays on your machine under `~/.kb/`.

## What it does today

| Capability | Where |
|---|---|
| Read the current webpage (title, structure, selection, text) | Chrome extension |
| Unified chat with page + memory context | Extension side panel |
| Explicit page save and quote capture | Extension → `/library/*` |
| Saved library (pages, quotes, per-page chat) | Extension + macOS app |
| Sparkles explore suggestions | Extension |
| Knowledge graph (pages, quotes, concepts) | Extension + macOS app |
| Screen capture + privacy pipeline | macOS app + `core/ingestion/` |
| Manual inputs (files, URLs, notes) | macOS app |
| Semantic search + connections | Backend API |

## Quick start

```bash
cp .env.example .env          # add OPENAI_API_KEY (optional)
python3 -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
node scripts/install-launcher.mjs   # auto-starts backend when extension opens
python3 main.py                     # or use the extension / Context.app
```

Load `chrome-extension/` unpacked in `chrome://extensions`, or install the macOS app:

```bash
bash scripts/install_app.sh
open -a Context
```

See [README.md](README.md) for the full documentation index.

## Architecture (summary)

```text
Chrome Extension (side panel) ──┐
                                ├──► Python backend :8765 ──► ~/.kb/
macOS Context.app ──────────────┘
Launcher :8798 (LaunchAgent) auto-starts backend when extension opens
```

Details: [architecture.md](architecture.md)

## LLM configuration

Set `KB_LLM_PROVIDER=auto` (default). With `OPENAI_API_KEY` set, chat and embeddings use
OpenAI; otherwise Ollama. All LLM calls go through `core/llm_providers.py` / `core/llm_service.py`.

## Data locations

| Path | Contents |
|---|---|
| `~/.kb/library/` | Saved pages, quotes, per-page chat |
| `~/.kb/graph/` | Concept knowledge graph |
| `~/.kb/index/` | Semantic embeddings |
| `~/.kb/events/` | Raw and clean event logs |
| `~/.kb/hashes/` | Name hash map and salt |

Reset options (symmetric in extension footer and desktop Settings):

- **Clear library** — saved pages, quotes, per-page chats (`POST /library/clear`)
- **Delete all data** — full `~/.kb/` wipe (`POST /delete-all`)

## API surface

Full reference: [api.md](api.md). Core library endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/ask` | Chat with page + memory context |
| `POST` | `/library/save-page` | Save a page + summary |
| `GET` | `/library/pages` | List saved pages |
| `GET` | `/library/pages/{id}` | Page detail + chat + quotes |
| `POST` | `/library/quotes` | Save a highlighted quote |
| `GET` | `/library/graph` | Graph nodes + edges |
| `POST` | `/library/clear` | Clear saved library only |
| `POST` | `/delete-all` | Wipe all runtime data |
