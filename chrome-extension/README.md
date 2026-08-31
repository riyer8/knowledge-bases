# Context Chrome Extension

Ask anything about the page you're reading. Connects to the local Python backend.

## Setup

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** and select this `chrome-extension/` folder
4. Copy the extension ID shown under **Context**
5. Register the native backend launcher (one-time):

```bash
bash chrome-extension/install-native-host.sh YOUR_EXTENSION_ID
```

Optional: save the ID so you do not need to pass it again:

```bash
echo YOUR_EXTENSION_ID > chrome-extension/.extension-id
bash chrome-extension/install-native-host.sh
```

6. Reload the extension in `chrome://extensions`
7. Open any webpage and click the Context icon

The extension will auto-start `python3 main.py` when the backend is not already running.

## Troubleshooting

- If you see a native messaging error, re-run `install-native-host.sh` with the correct extension ID
- Backend logs: `.kb_backend.log` in the repo root
- Manual start: `python3 main.py` or `bash scripts/start_backend.sh`

## Configuration

Set your LLM provider in the repo `.env`:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
KB_LLM_PROVIDER=auto
```

With `auto`, OpenAI is used automatically when the key is set.

## Features

- Auto-starts the local backend via native messaging
- Extracts structured page context (title, headings, selection, visible text)
- Four modes: Understand, Connect, Learn, Explore
- Streams answers from `POST /ask`
- Saves quotes from the side panel when you highlight text (sidebar only — no on-page popup)
- Shows related prior reading from `GET /connections`
