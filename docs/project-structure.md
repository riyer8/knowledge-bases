# Project Structure

```text
knowledge-bases/
├── core/                          # Python backend
│   ├── config.py                  # Central config (KB_ROOT, ports, LLM)
│   ├── frontend_backend.py        # HTTP router — all clients
│   ├── llm_providers.py           # OpenAI / Anthropic / Ollama
│   ├── library_service.py         # Saved pages, quotes, explore
│   ├── page_context_service.py    # Page ingest, search, connections
│   ├── ingestion/                 # Screenshot OCR, text ingest, events
│   ├── privacy/                   # PII detection, hashing, sensitive sites
│   ├── memory/                    # Embeddings, graph, concept graph, buckets
│   ├── retrieval/                 # RAG chat, page chat, context assembly
│   ├── integrations/              # GCal, Gmail, OAuth
│   └── proactive/                 # Pattern detection, insights
├── chrome-extension/
│   ├── manifest.json
│   ├── background.js              # Launcher + backend health
│   ├── lib/launcher.js            # HTTP auto-start client (:8798)
│   ├── content/extract.js         # Page extraction
│   ├── sidepanel/                 # Quotes | Chat, library, graph
│   └── install-native-host.sh     # Legacy optional path
├── DesktopApp/
│   └── DesktopApp/
│       ├── App/                   # App delegate, menu bar, hotkeys
│       ├── Windows/               # MainWindow, ManualInputsWindow
│       ├── Views/                 # Chat, Library, Graph, Settings, Pet
│       ├── Services/              # BackendService, LibraryStore
│       └── Models/                # DesktopPetSettings
├── docs/                          # All documentation (start at docs/README.md)
│   ├── specs/                     # Event schema, privacy, buckets, anonymization
│   └── traces/                    # Optional session logs
├── scripts/
│   ├── start_backend.sh           # Backend launcher
│   ├── launcher.mjs               # LaunchAgent HTTP service
│   ├── install-launcher.mjs       # One-time launcher install
│   ├── install_app.sh             # Build + install Context.app
│   └── generate_app_icon.py
├── tests/                         # pytest + privacy eval fixtures
├── demo/seed_demo.py              # Presentation seed data
├── main.py                        # Backend entry point
├── start.sh / stop.sh             # Backend lifecycle
├── init.md                      # Session protocol (repo root)
```

Runtime data: `~/.kb/` (see [storage.md](storage.md)). Not in the repo.

## Hotkeys (macOS app — ⌘⇧)

| Key | Action |
|---|---|
| `C` | Open chat |
| `G` | Open graph |
| `W` | Close main window |
| `S` | Screenshot capture |

## Documentation

Start at [docs/README.md](docs/README.md). Key references:

- [Configuration](configuration.md) — all env vars
- [Storage](storage.md) — `~/.kb/` layout
- [Constitution](constitution.md) — full engineering rules
