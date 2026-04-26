# Knowledge Bases

Desktop pet prototype with a SwiftUI macOS frontend and a lightweight Python backend for manual input ingestion.

## Structure

- `DesktopApp/DesktopApp/PetView.swift`: pet icon and interaction surface.
- `DesktopApp/DesktopApp/ChatWindow.swift`: chat window UI and manual input frontend.
- `inputs/manual/manual_input_server.py`: Python backend that receives manual inputs.
- `inputs/manual/files/`: uploaded file copies written by backend at runtime.
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
- `GET /health`
  - Returns service status and write path
