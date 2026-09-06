# Getting Started

_Last updated: 2026-09-06_

## Quick Start

From repo root:

```bash
python3 main.py
```

Or use the one-click launcher:

```bash
bash start.sh
```

To stop the backend:

```bash
bash stop.sh
```

Health check:

```bash
curl http://127.0.0.1:8765/health
```

## Environment

Copy `.env.example` to `.env` and configure as needed:

```bash
cp .env.example .env
```

Key variables — full reference: [configuration.md](configuration.md).

| Variable | Default | Purpose |
|---|---|---|
| `KB_ROOT` | `~/.kb` | Local storage root |
| `KB_CHAT_MODEL` | `qwen2.5:3b` | Ollama model for chat |
| `KB_EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `KB_PORT` | `8765` | Backend HTTP port |
| `KB_LLM_PROVIDER` | `auto` | `auto`, `ollama`, `openai`, or `anthropic` |
| `OPENAI_API_KEY` | — | Set this to use OpenAI (auto-detected) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `KB_EMBED_PROVIDER` | `auto` | `auto`, `ollama`, or `openai` |
| `KB_PROACTIVE_INTERVAL_MINUTES` | `20` | Desktop proactive check cadence |

### Using OpenAI (recommended if you have a key)

```bash
cp .env.example .env
```

Edit `.env`:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
KB_LLM_PROVIDER=auto
KB_EMBED_PROVIDER=auto
```

With `auto`, chat and semantic search both use OpenAI when the key is set — no Ollama required.
`start.sh` also skips pulling/starting Ollama when `OPENAI_API_KEY` is set.

## Chrome Extension

1. **One-time launcher install** (auto-starts backend when you open the extension):

```bash
node scripts/install-launcher.mjs
```

2. Load unpacked from `chrome-extension/` in `chrome://extensions`
3. Reload the extension and open Context on any page

See [chrome-extension/README.md](../chrome-extension/README.md) for details.

## LLM Providers

| Provider | Required env vars |
|---|---|
| `auto` (default) | Uses OpenAI when `OPENAI_API_KEY` is set, else Ollama |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `ollama` | `KB_CHAT_MODEL`, Ollama running locally |
| `anthropic` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |

Chat and page Q&A go through `core/llm_providers.py` (`KB_LLM_PROVIDER`). Anthropic supports
chat only; embeddings require Ollama or OpenAI.

## Dependencies

- Python 3.11+
- Ollama (for local models) — `start.sh` handles model pulls unless `OPENAI_API_KEY` is set
- Xcode (for the macOS app)
- Node + Playwright (optional) for `scripts/e2e_browser_smoke.mjs` — `npm install`

Install Python dependencies:

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Run tests:

```bash
pytest tests/
```

Privacy eval cases (20+ JSON fixtures):

```bash
pytest tests/test_privacy_eval_cases.py -v
```

See [testing.md](testing.md) for details.

## Demo data

For presentations or walkthroughs, seed the knowledge base with Symsys 161 demo events
(capture-to-retrieval loop, course themes, presentation tips):

```bash
python3 demo/seed_demo.py
```

This writes five sample events into `~/.kb/` via the normal ingestion pipeline. After
seeding, start the app and ask chat about **Symsys161** or your class presentation — answers
should be fast and on-topic. Re-run anytime to add more demo context (events are appended,
not deduplicated).

## Obsidian (optional; wiki archived from nav)

Wiki APIs and `~/.kb/wiki/` still work. Life/Wiki are [archived from extension/dashboard nav](archived.md);
Desktop may still show Wiki. To browse the vault in Obsidian:

1. Install [Obsidian](https://obsidian.md/)
2. **Open folder as vault** → select `~/.kb/wiki/`
3. Browse `articles/`, `raw/`, and `index.md`

Context auto-writes most wiki content via **Compile** when that flow is used. Manual markdown edits in the vault are fine.

## macOS App

**Context** is a real macOS application (`Context.app`) — the same kind of thing you see in
your Applications folder. The `DesktopApp/` folder in this repo is just the source code.

### Install to Applications (recommended)

```bash
bash scripts/install_app.sh
```

This builds the app and copies it to `/Applications/Context.app`. After that, open it from
Applications, Spotlight, or:

```bash
open -a Context
```

On launch, the app auto-starts the Python backend. Your knowledge data stays in `~/.kb/`.

The app includes **Chat**, **Library** (saved pages/quotes; notes document parity is extension + dashboard today),
**Graph**, **Life**, **Wiki**, **Settings**, and **Manual Inputs** panels.

Configure API keys in the macOS app **Settings** panel or the Chrome extension **Settings**
tab (gear icon). Both use `GET` / `POST /settings` to read and update `.env` — see
[configuration.md](configuration.md).

### Build without installing

```bash
bash scripts/build_app.sh
open DesktopApp/build/DerivedData/Build/Products/Debug/Context.app
```

Or build in Xcode: open `DesktopApp/DesktopApp.xcodeproj` and press **⌘B**.

After the first build, `start.sh` can also launch the app automatically.

The app appears in the Dock with its own icon and menu bar. Use **⌘⇧C** for chat, **⌘⇧G** for graph,
**⌘⇧P** for the proactive popup, **⌘⇧S** / **⌘⇧I** for screenshots.

The Swift frontend connects to the backend at `http://127.0.0.1:8765`. Both the Chrome extension
and macOS app share the same backend and storage root (`~/.kb/`). See [architecture.md](architecture.md).

To regenerate the app icon: `python3 scripts/generate_app_icon.py`
