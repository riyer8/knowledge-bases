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
│   ├── frontend_backend.py              # unified backend HTTP router
│   ├── data_reset_service.py            # delete-all runtime data cleanup
│   ├── llm_service.py                   # LLM calls + fallback behavior
│   ├── graph_service.py                 # markdown graph builder logic
│   ├── manual_input_service.py          # manual input storage + processing
│   ├── chat_prompt.txt                  # base system prompt
│   ├── config.py                        # centralized path + env config
│   ├── ingestion/                       # data capture pipeline
│   ├── privacy/                         # PII detection, hashing, sensitive sites
│   ├── memory/                          # chunking, embeddings, graph, vector store
│   ├── retrieval/                       # semantic search, context assembly, chat
│   ├── integrations/                    # GCal, Gmail, OAuth
│   └── proactive/                       # pattern detection, insight surfacing
├── inputs/
│   ├── manual/
│   │   ├── manual_input_server.py       # manual-input-only backend
│   │   ├── entries.jsonl                # runtime manual-input event log
│   │   └── uploads/
│   │       ├── files/
│   │       ├── text/
│   │       └── urls/
│   ├── screenshot/
│   │   └── screenshot_service.py        # screenshot capture service
│   └── .graph-dependencies.json         # manual graph edges (created at runtime)
├── chrome-extension/                    # Chrome side panel extension
│   ├── manifest.json
│   ├── background.js
│   ├── install-native-host.sh           # one-time auto-start setup
│   ├── native-host/context_host.py
│   ├── content/extract.js
│   └── sidepanel/
├── scripts/
│   └── start_backend.sh                 # backend launcher for extension
├── docs/                                # product + developer documentation
├── tests/
├── SPECS/
├── STATE/
├── TASKS/
├── DECISIONS/
├── EVALS/
└── main.py                              # root launcher for frontend backend
```

## Hotkeys (Cmd + Shift)

| Key | Action |
|---|---|
| `C` | Open chat tab |
| `G` | Open graph tab |
| `W` | Close chat window |
| `S` | Trigger backend screenshot capture |
