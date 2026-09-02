# Project Structure

```text
knowledge-bases/
├── DesktopApp/
│   └── DesktopApp/
│       ├── App/                         # app delegate, pet window, hotkeys
│       ├── Windows/                     # MainWindow, ManualInputsWindow
│       ├── Views/                       # Chat, Library, Graph, Settings, Pet
│       ├── Services/                    # BackendService, LibraryStore
│       └── Models/                      # DesktopPetSettings
├── core/
│   ├── frontend_backend.py              # unified HTTP router (all clients)
│   ├── config.py                        # centralized path + env config
│   ├── llm_providers.py                 # OpenAI / Anthropic / Ollama
│   ├── library_service.py               # saved pages, quotes, explore
│   ├── page_context_service.py          # page ingest, search, connections
│   ├── ingestion/                       # screenshot OCR, text ingest
│   ├── privacy/                         # PII detection, hashing, sensitive sites
│   ├── memory/                          # embeddings, graph, concept graph
│   ├── retrieval/                       # semantic search, chat, page chat
│   ├── integrations/                    # GCal, Gmail, OAuth
│   └── proactive/                       # pattern detection, insights
├── chrome-extension/
│   ├── manifest.json
│   ├── background.js                    # launcher + backend health
│   ├── lib/launcher.js                  # HTTP auto-start client
│   ├── content/extract.js               # page extraction
│   └── sidepanel/                       # Quotes | Chat, saved library, graph
├── scripts/
│   ├── start_backend.sh                 # backend launcher
│   ├── launcher.mjs                     # LaunchAgent HTTP service (:8798)
│   ├── install-launcher.mjs             # one-time launcher install
│   ├── install_app.sh                   # build + install Context.app
│   └── generate_app_icon.py
├── docs/                                # all product + engineering documentation
├── tests/                               # unit tests + privacy eval fixtures
├── demo/                                # seed script for presentations
├── main.py                              # backend entry point
├── start.sh                             # one-click backend + app launcher
├── CLAUDE.md                            # engineering constitution
└── init.md                              # AI session protocol
```

Runtime data is stored under `~/.kb/` (not in the repo). See [architecture.md](architecture.md).

## Hotkeys (macOS app — Cmd + Shift)

| Key | Action |
|---|---|
| `C` | Open chat tab |
| `G` | Open graph tab |
| `W` | Close main window |
| `S` | Trigger backend screenshot capture |

## Documentation map

Everything else lives in [docs/README.md](README.md).
