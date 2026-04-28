# Knowledge Bases

Personal knowledge bases

## Project Tree

```text
knowledge-bases/
├── DesktopApp/
│   └── DesktopApp/
│       ├── App/
│       │   └── DesktopAppApp.swift      # app delegate, pet window, hotkeys
│       ├── Windows/
│       │   ├── MainWindow.swift         # main window controller + core panels
│       │   └── ManualInputsWindow.swift # detached manual-inputs window
│       ├── Views/
│       │   ├── SettingsPanel.swift      # settings UI (theme, icon, delete-all)
│       │   ├── PetView.swift            # desktop pet icon/avatar surface
│       │   ├── ChatWindow.swift         # chat panel UI
│       │   └── GraphWindow.swift        # graph panel UI
│       └── Models/
│           └── DesktopPetSettings.swift # persisted app settings model
├── core/
│   ├── frontend_backend.py              # unified backend HTTP router
│   ├── data_reset_service.py            # delete-all runtime data cleanup
│   ├── llm_service.py                   # Claude call + fallback behavior
│   ├── graph_service.py                 # markdown graph builder logic
│   ├── manual_input_service.py          # manual input storage + processing
│   └── chat_prompt.txt                  # base system prompt
├── inputs/
│   ├── manual/
│   │   ├── manual_input_server.py       # manual-input-only backend
│   │   ├── entries.jsonl                # runtime manual-input event log
│   │   └── uploads/
│   │       ├── files/                   # copied uploaded files
│   │       ├── text/                    # text inputs as markdown
│   │       └── urls/                    # URL inputs as markdown
│   ├── screenshot/
│   │   └── screenshot_service.py        # screenshot capture service
│   └── .graph-dependencies.json         # manual graph edges (created at runtime)
└── main.py                              # root launcher for frontend backend
```

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
  - Returns saved entries (newest first; frontend manual log view renders oldest -> newest and auto-scrolls to latest)
- `POST /chat`
  - JSON body:
    - `prompt`: user prompt string
  - Uses `core/chat_prompt.txt` as system prompt and calls Claude when `.env` contains a real `CLAUDE_CODE_API_KEY`
- `GET /graph`
  - Returns markdown graph nodes/edges and supports query params:
    - `orphans=1`
    - `unlinked=1`
    - `folder=<folder-prefix>`
- `POST /graph/dependency`
  - JSON body:
    - `source`: source node id/path
    - `target`: target node id/path
  - Creates a manual dependency edge between two graph nodes
- `POST /screenshot`
  - Captures current screen and saves to `inputs/screenshot/captures/`
- `POST /delete-all`
  - Deletes local runtime data:
    - `inputs/manual/` (manual uploads + log)
    - `inputs/.graph-dependencies.json`
    - `inputs/screenshot/captures/`
- `GET /health`
  - Returns service status and write path

The Swift frontend in `DesktopApp/DesktopApp/Views/ChatWindow.swift` is already wired to this backend at `http://127.0.0.1:8765`.

## Hotkeys (Cmd + Shift)

- `C`: open chat tab
- `G`: open graph tab
- `W`: close chat window
- `S`: trigger backend screenshot capture
