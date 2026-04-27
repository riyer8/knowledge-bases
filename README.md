# Knowledge Bases

Desktop pet prototype with a SwiftUI macOS frontend and a lightweight Python backend.

## Structure

- `DesktopApp/DesktopApp/PetView.swift`: pet icon and interaction surface.
- `DesktopApp/DesktopApp/ChatWindow.swift`: chat window UI and manual input frontend.
- `main.py`: root launcher for the frontend backend service.
- `core/frontend_backend.py`: unified backend used by `ChatWindow.swift` and graph/manual tabs.
- `core/llm_service.py`: Claude call + fallback behavior.
- `core/graph_service.py`: markdown graph builder logic.
- `core/manual_input_service.py`: manual input storage and entry processing.
- `inputs/manual/manual_input_server.py`: manual-input-only backend (no chat/graph/LLM logic).
- `core/chat_prompt.txt`: base system prompt used by Python chat backend.
- `inputs/screenshot/screenshot_service.py`: Python screenshot capture service used by backend endpoint.
- `inputs/manual/uploads/files/`: uploaded file copies written by backend at runtime.
- `inputs/manual/uploads/text/`: raw text inputs saved as `.md` files.
- `inputs/manual/uploads/urls/`: URL inputs saved as `.md` files.
- `inputs/manual/entries.jsonl`: runtime manual-input event log.

## Run Backend For Frontend

From repo root:

```bash
python3 main.py
```

The backend loads chat settings from root `.env`. A scaffold placeholder is included:

```bash
CLAUDE_CODE_API_KEY=REPLACE_WITH_CLAUDE_CODE_API_KEY
CLAUDE_CODE_MODEL=claude-3-5-sonnet-latest
```

If `CLAUDE_CODE_API_KEY` is still the placeholder (or empty), `POST /chat` returns a default fallback reply so the frontend flow still works.

Manual-input-only server (optional, for isolated manual ingestion testing):

```bash
python3 inputs/manual/manual_input_server.py
```

Health check:

```bash
curl http://127.0.0.1:8765/health
```

Optional custom storage root for `main.py`:

```bash
KB_MANUAL_INPUT_ROOT="/absolute/path/to/inputs/manual" KB_SCREENSHOT_ROOT="/absolute/path/to/screenshot/captures" python3 main.py
```

Optional custom storage root for manual-input-only server:

```bash
KB_MANUAL_INPUT_ROOT="/absolute/path/to/inputs/manual" python3 inputs/manual/manual_input_server.py
```

## Backend API

- `POST /manual-input`
  - JSON body:
    - `kind`: `file` | `url` | `text`
    - `value`: file path (for `file`) or raw content string
    - `createdAt`: ISO timestamp
- `GET /manual-inputs`
  - Returns saved entries (newest first)
- `POST /chat`
  - JSON body:
    - `prompt`: user prompt string
  - Uses `core/chat_prompt.txt` as system prompt and calls Claude when `.env` contains a real `CLAUDE_CODE_API_KEY`
- `GET /graph`
  - Returns markdown graph nodes/edges and supports query params:
    - `orphans=1`
    - `unlinked=1`
    - `folder=<folder-prefix>`
- `POST /screenshot`
  - Captures current screen and saves to `inputs/screenshot/captures/`
- `GET /health`
  - Returns service status and write path

The Swift frontend in `DesktopApp/DesktopApp/ChatWindow.swift` is already wired to this backend at `http://127.0.0.1:8765`.

## Hotkeys (Cmd + Shift)

- `C`: open chat tab
- `G`: open graph tab
- `W`: close chat window
- `S`: trigger backend screenshot capture
