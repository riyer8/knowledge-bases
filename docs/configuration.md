# Configuration

_Last updated: 2026-09-09_

All configuration flows through `core/config.py` and `.env`. Copy `.env.example` to `.env`
at the repo root.

```bash
cp .env.example .env
```

---

## Environment variables

### Storage and server

| Variable | Default | Purpose |
|---|---|---|
| `KB_ROOT` | `~/.kb` | Local storage root for all runtime data |
| `KB_PORT` | `8765` | Backend HTTP port |

### LLM — chat

| Variable | Default | Purpose |
|---|---|---|
| `KB_LLM_PROVIDER` | `auto` | `auto`, `ollama`, `openai`, or `anthropic` |
| `KB_CHAT_MODEL` | `qwen2.5:3b` | Ollama chat model (when provider is ollama) |
| `OPENAI_API_KEY` | — | Enables OpenAI when set (`auto` picks this) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-latest` | Anthropic chat model |

With `KB_LLM_PROVIDER=auto`, OpenAI is used when `OPENAI_API_KEY` is set; otherwise Ollama.

### LLM — embeddings

| Variable | Default | Purpose |
|---|---|---|
| `KB_EMBED_PROVIDER` | `auto` | `auto`, `ollama`, or `openai` |
| `KB_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |

### Google integrations

| Variable | Purpose |
|---|---|
| `KB_GCAL_CLIENT_ID` | Google Calendar OAuth client ID |
| `KB_GCAL_CLIENT_SECRET` | Google Calendar OAuth secret |
| `KB_GMAIL_CLIENT_ID` | Gmail OAuth client ID |
| `KB_GMAIL_CLIENT_SECRET` | Gmail OAuth secret |

Scopes: Calendar and Gmail **read-only**. See [getting-started.md](getting-started.md).

### Proactive insights

| Variable | Default | Purpose |
|---|---|---|
| `KB_PROACTIVE_INTERVAL_MINUTES` | `20` | Minutes between desktop proactive checks (also via `POST /settings`) |

### macOS app

| Variable | Purpose |
|---|---|
| `CONTEXT_REPO_ROOT` | Override repo path for backend auto-start in Context.app |

---

## Launcher (Chrome extension)

The extension uses a separate HTTP launcher (defaults below). `node scripts/install-launcher.mjs` registers a LaunchAgent that starts `python3 main.py` when the extension opens.

| Variable | Default | Purpose |
|---|---|---|
| `CONTEXT_LAUNCHER_PORT` | `8798` | Launcher HTTP port (`scripts/launcher.mjs`) |
| `KB_API_URL` | `http://127.0.0.1:8765` | URL the launcher health-checks before spawning the backend |

These are process environment variables for the launcher, not required in `.env` for the Python backend. They are documented in `.env.example` so a from-scratch setup sees every knob the code reads.

---

## Python config object

Import anywhere:

```python
from core.config import config

config.kb_root          # Path
config.backend_port     # int
config.llm_provider     # str
config.ensure_dirs()    # create ~/.kb structure
```

Path properties: `pages_dir`, `events_raw_dir`, `events_clean_dir`, `index_dir`, `graph_dir`,
`hashes_dir`, `buckets_dir`, `auth_dir`, `paused_log`, `hash_map_path`, `hash_salt_path`,
`wiki_dir`, `wiki_raw_dir`, `wiki_articles_dir`, `wiki_outputs_dir`.

Library data (`~/.kb/library/`) is managed by `core/library_service.py`.
Relationship profiles live under `~/.kb/relationships/` via `core/memory/relationships.py`.

---

## Runtime settings API

Clients (Chrome extension, macOS app) can read and update allowed `.env` keys without
editing the file manually:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/settings` | Current provider, model names, masked key hints, setup notes |
| `POST` | `/settings` | Update provider, API keys, models (writes `.env`, reloads config) |

Allowed `POST` body fields: `llm_provider`, `openai_api_key`, `anthropic_api_key`,
`openai_model`, `chat_model`, `embed_provider`, `proactive_interval_minutes`.

Full request/response shapes: [api.md](api.md#settings-all-clients). Environment variable reference
is in the tables above.

---

## Recommended setups

### OpenAI (simplest)

```bash
OPENAI_API_KEY=sk-...
KB_LLM_PROVIDER=auto
KB_EMBED_PROVIDER=auto
```

No Ollama required.

### Local-only (Ollama)

```bash
KB_LLM_PROVIDER=ollama
KB_EMBED_PROVIDER=ollama
KB_CHAT_MODEL=qwen2.5:3b
KB_EMBED_MODEL=nomic-embed-text
```

Run `ollama pull qwen2.5:3b` and `ollama pull nomic-embed-text`.
