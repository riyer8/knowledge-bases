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

Key variables:

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

1. Load unpacked from `chrome-extension/` in `chrome://extensions`
2. One-time native host install (auto-starts backend on click):

```bash
bash chrome-extension/install-native-host.sh YOUR_EXTENSION_ID
```

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

## Custom Storage Paths

```bash
KB_MANUAL_INPUT_ROOT="/absolute/path/to/inputs/manual" \
KB_SCREENSHOT_ROOT="/absolute/path/to/screenshot/captures" \
python3 main.py
```

## Manual Input Server (Optional)

For isolated manual-ingestion testing:

```bash
python3 inputs/manual/manual_input_server.py
```

With custom storage:

```bash
KB_MANUAL_INPUT_ROOT="/absolute/path/to/inputs/manual" \
python3 inputs/manual/manual_input_server.py
```

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
