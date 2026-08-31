# Project Structure

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
│       │   ├── GraphWindow.swift        # graph panel UI
│       │   └── ProactivePopup.swift     # proactive insight pop-ups
│       └── Models/
│           └── DesktopPetSettings.swift # persisted app settings model
├── core/
│   ├── frontend_backend.py              # unified HTTP router (all clients)
│   ├── config.py                        # centralized path + env config
│   ├── llm_providers.py                 # OpenAI / Anthropic / Ollama abstraction
│   ├── llm_service.py                   # legacy LLM wrapper
│   ├── library_service.py               # saved pages, quotes, explore
│   ├── page_context_service.py          # page ingest, search, connections
│   ├── chat_prompt.txt                  # base system prompt
│   ├── ingestion/                       # screenshot OCR, text ingest, event writer
│   ├── privacy/                         # PII detection, hashing, sensitive sites
│   ├── memory/                          # chunking, embeddings, graph, concept graph
│   ├── retrieval/                       # semantic search, chat, page chat
│   ├── integrations/                    # GCal, Gmail, OAuth
│   └── proactive/                       # pattern detection, insight surfacing
├── chrome-extension/
│   ├── manifest.json
│   ├── background.js
│   ├── install-native-host.sh           # one-time auto-start setup
│   ├── native-host/context_host.py
│   ├── content/extract.js
│   └── sidepanel/                       # chat, saved library, graph UI
├── inputs/
│   ├── manual/
│   │   ├── manual_input_server.py       # optional isolated manual-input server
│   │   └── uploads/                     # runtime uploads (gitignored)
│   └── screenshot/
│       └── screenshot_service.py        # screenshot capture service
├── scripts/
│   └── start_backend.sh                 # backend launcher for extension
├── docs/                                # product + developer documentation
├── tests/
├── SPECS/
├── STATE/
├── TASKS/
├── DECISIONS/
├── EVALS/
├── main.py                              # root launcher for frontend backend
├── start.sh                             # one-click backend + app launcher
└── goal.md                              # living project status
```

Runtime data is stored under `~/.kb/` (not in the repo). See [architecture.md](architecture.md).

## Hotkeys (macOS app — Cmd + Shift)

| Key | Action |
|---|---|
| `C` | Open chat tab |
| `G` | Open graph tab |
| `W` | Close chat window |
| `S` | Trigger backend screenshot capture |
