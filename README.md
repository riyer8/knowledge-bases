# Knowledge Bases

Desktop pet prototype with a SwiftUI macOS frontend and a lightweight Python backend for manual input ingestion.

## Structure

- `DesktopApp/DesktopApp/PetView.swift`: pet icon and interaction surface.
- `DesktopApp/DesktopApp/ChatWindow.swift`: chat window UI and manual input frontend.
- `inputs/manual/manual_input_server.py`: Python backend that receives manual inputs.
- `inputs/screenshot/screenshot_service.py`: Python screenshot capture service used by backend endpoint.
- `inputs/manual/uploads/files/`: uploaded file copies written by backend at runtime.
- `inputs/manual/uploads/text/`: raw text inputs saved as `.md` files.
- `inputs/manual/uploads/urls/`: URL inputs saved as `.md` files.
- `inputs/manual/entries.jsonl`: runtime manual-input event log.

## Run Manual Input Backend

From repo root:

```bash
python3 inputs/manual/manual_input_server.py
```

Health check:

```bash
curl http://127.0.0.1:8765/health
```

Optional custom storage root:

```bash
KB_MANUAL_INPUT_ROOT="/absolute/path/to/inputs/manual" KB_SCREENSHOT_ROOT="/absolute/path/to/screenshot/captures" python3 inputs/manual/manual_input_server.py
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
- `GET /graph`
  - Returns markdown graph nodes/edges and supports query params:
    - `orphans=1`
    - `unlinked=1`
    - `folder=<folder-prefix>`
- `POST /screenshot`
  - Captures current screen and saves to `inputs/screenshot/captures/`
- `GET /health`
  - Returns service status and write path

## Hotkeys (Cmd + Shift)

- `C`: open chat tab
- `G`: open graph tab
- `W`: close chat window
- `S`: trigger backend screenshot capture
