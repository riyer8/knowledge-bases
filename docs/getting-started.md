# Getting Started

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

## Legacy Claude path

For Claude API chat (legacy desktop path), set in `.env`:

```bash
CLAUDE_CODE_API_KEY=your_key_here
CLAUDE_CODE_MODEL=claude-3-5-sonnet-latest
```

If `CLAUDE_CODE_API_KEY` is unset or still the placeholder, `POST /chat` returns a default fallback reply so the frontend flow still works.

## Dependencies

- Python 3.11+
- Ollama (for local models) — `start.sh` handles model pulls
- Xcode (for the macOS app)

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

## Obsidian (optional IDE)

Open your wiki as an Obsidian vault for reading and editing compiled articles:

1. Install [Obsidian](https://obsidian.md/)
2. **Open folder as vault** → select `~/.kb/wiki/`
3. Browse `articles/`, `raw/`, and `index.md` — the same files the web UI and extension use

Context auto-writes most wiki content via **Compile**; you can edit markdown directly when you want control. Use the Obsidian Web Clipper to save articles into `wiki/raw/` (or save via the extension and tap **+ Wiki**).

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

The app includes **Chat**, **Library** (saved pages and quotes from the extension),
**Graph**, **Life** (bucket review), **Settings**, and **Manual Inputs** panels.

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

The app appears in the Dock with its own icon and menu bar. Use **⌘⇧C** for chat, **⌘⇧G** for graph.

The Swift frontend connects to the backend at `http://127.0.0.1:8765`. Both the Chrome extension
and macOS app share the same backend and storage root (`~/.kb/`). See [architecture.md](architecture.md).

To regenerate the app icon: `python3 scripts/generate_app_icon.py`
