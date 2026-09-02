# Context Chrome Extension

Ask anything about the page you're reading. Connects to the local Python backend.

## Setup

1. **Install the launcher** (one time — same pattern as [apt-hunter](https://github.com/riyer8/apt-hunter)):

```bash
node scripts/install-launcher.mjs
```

This registers a small helper that runs on login. When you open the extension, it starts `python3 main.py` automatically.

2. Load the extension in Chrome:
   - Open `chrome://extensions`
   - Enable **Developer mode**
   - **Load unpacked** → select this `chrome-extension/` folder
3. Reload the extension, open any normal webpage, click **Context**

No extension ID or native messaging setup required for normal use.

## Side panel tabs

| Tab | Purpose |
|---|---|
| **Page** | Current tab — save quotes, chat, edit title/metadata |
| **Saved** | Saved pages with summaries and history |
| **Life** | Review auto-classified activity buckets |
| **Graph** | Saved pages linked by shared topics |
| **Settings** (gear) | API keys, backend status, data controls |

## Troubleshooting

| Issue | Fix |
|---|---|
| Backend doesn't start | Run `node scripts/install-launcher.mjs`, reload extension |
| Buttons do nothing | Check footer says **Ready**; open **Settings** → Retry |
| Can't save on chrome:// pages | Use a normal website (not Chrome internal pages) |
| Still stuck | `python3 main.py` manually, then **Retry** in Settings |
| Launcher logs | `~/Library/Logs/Context/` |
| Backend logs | `.kb_backend.log` in the repo root |

### Legacy: native messaging (optional)

If you prefer Chrome native messaging instead of the launcher:

```bash
bash chrome-extension/install-native-host.sh YOUR_EXTENSION_ID
```

## Configuration

Set your LLM provider in the repo `.env`, or use the extension **Settings** tab (gear icon):

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
KB_LLM_PROVIDER=auto
```

## Features

- Auto-starts the local backend when you open the extension
- Extracts structured page context (title, headings, selection, visible text, author/date hints)
- PDF text extraction via backend
- On-page highlight toolbar + saved quotes (edit/delete in panel)
- Unified chat with streaming via `POST /ask`
- Collapsible metadata (author, date, custom fields)
- In-panel confirm dialogs (no Chrome system alerts)
- Proactive insight banner (dismissible)
- Knowledge graph: saved pages only, linked by shared topics
