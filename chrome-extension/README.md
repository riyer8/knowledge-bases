# Context Chrome Extension

Highlight passages like [Obsidian Web Clipper](https://obsidian.md/clipper), keep notes locally, copy bookshelf JSON onto your site. Connects to the local Python backend — no full-page markdown clip, just the passages you choose.

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

## Clipper flow

1. Select text on the page
2. Click **Highlight** (or press **⌥H / Alt+H**) — optional note in the floating bar
3. The passage lands in **Notes**; yellow marks stay on the page when you return
4. Click a mark to peek at its note, or **Open in Notes**
5. Fill Details (author, tags, TLDR) and **Copy JSON** onto your site

| Shortcut | Action |
|---|---|
| **⌥H / Alt+H** | Highlight current selection |
| **⌥N / Alt+N** | Open Context → Notes |
| Change keys | `chrome://extensions/shortcuts` |

## Side panel tabs

| Tab | Purpose |
|---|---|
| **Page** | Current tab — Details, Notes, Chat |
| **Saved** | Saved pages with the same notes document |
| **Graph** | Saved pages linked by shared topics |
| **Settings** (gear) | API keys, backend status, data controls |

Life and Wiki are [archived](../docs/archived.md) (hidden from nav).

## Page panels

| Panel | Purpose |
|---|---|
| **Details** | Title, author, category, TLDR, tags, bookshelf JSON preview |
| **Notes** | Quotes you saved plus your commentary (source of truth for Copy JSON) |
| **Chat** | Ask about this page (`POST /ask`) |

## Troubleshooting

| Issue | Fix |
|---|---|
| Backend doesn't start | Run `node scripts/install-launcher.mjs`, reload extension |
| Buttons do nothing | Check footer says **Ready**; open **Settings** → Retry |
| Can't save on chrome:// pages | Use a normal website (not Chrome internal pages) |
| Shortcut conflict | Remap in `chrome://extensions/shortcuts` |
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

- Lightweight on-page highlight bar (works with the side panel closed)
- Hotkeys for highlight and open Notes
- Highlights persist and repaint when you revisit a page
- Notes editor: quotes + your commentary; Copy JSON matches the document (`:::quote` fences)
- Extracts structured page context for chat
- PDF text extraction via backend
- Unified chat with streaming via `POST /ask`
- Knowledge graph: saved pages linked by shared topics
