# Project Structure

_Last updated: 2026-09-06_

```text
knowledge-bases/
├── core/                          # Python backend
│   ├── config.py                  # Central config (KB_ROOT, ports, LLM)
│   ├── env_settings.py            # GET/POST /settings — .env read/write
│   ├── frontend_backend.py        # HTTP entry — wires route mixins
│   ├── http/                      # Route mixins (library, buckets, relationships, wiki, /app/)
│   ├── llm_providers.py           # OpenAI / Anthropic / Ollama
│   ├── library_service.py         # Saved pages, quotes, notes metadata, PDF extract, explore
│   ├── wiki_service.py            # Raw ingest, LLM compile, wiki health
│   ├── page_context_service.py    # Page ingest, search, connections
│   ├── ingestion/                 # Screenshot OCR, text ingest, event_writer
│   ├── privacy/                   # PII detection, hashing, sensitive sites
│   ├── memory/                    # Embeddings, graph, concept graph, buckets, relationships
│   ├── retrieval/                 # RAG chat, page chat, context assembly
│   ├── integrations/              # GCal, Gmail, iMessage, OAuth
│   └── proactive/                 # Pattern detection, insights, life balance
├── chrome-extension/
│   ├── manifest.json
│   ├── background.js              # Launcher + page context + PDF extract
│   ├── lib/launcher.js            # HTTP auto-start client (:8798)
│   ├── content/                   # extract.js, highlights.js (on-page quotes)
│   ├── sidepanel/                 # Page | Saved | Graph + Settings
│   │   ├── index.html
│   │   ├── panel.css
│   │   ├── page-drafts.js         # Local drafts until Save
│   │   ├── notes.js               # Notes markdown ↔ HTML ↔ :::quote
│   │   └── bookshelf-export.js    # Copy-paste JS object for a personal site
│   └── install-native-host.sh     # Legacy optional path
├── DesktopApp/
│   └── DesktopApp/
│       ├── App/                   # App delegate, menu bar, hotkeys
│       ├── Windows/               # MainWindow, ManualInputsWindow
│       ├── Views/                 # Chat, Library, Graph, Life, Wiki, Settings, Pet
│       ├── Services/              # BackendService, LibraryStore, WikiStore, LifeStore
│       └── Models/                # DesktopPetSettings
├── docs/                          # All documentation (start at docs/README.md)
│   ├── specs/                     # Event schema, privacy, buckets, notes-export, …
│   └── traces/                    # Optional session logs
├── scripts/
│   ├── start_backend.sh           # Backend launcher (used by native host / app)
│   ├── launcher.mjs               # LaunchAgent HTTP service
│   ├── install-launcher.mjs       # One-time launcher install
│   ├── install_app.sh             # Build + install Context.app
│   ├── build_app.sh               # Build Context.app without installing
│   ├── e2e_smoke.py               # API smoke against running backend
│   ├── e2e_browser_smoke.mjs      # Playwright extension reading-loop smoke
│   └── generate_app_icon.py
├── tests/                         # pytest + privacy eval fixtures + node helpers
├── web/                           # Local dashboard (served at /app/)
├── demo/seed_demo.py              # Presentation seed data
├── main.py                        # Backend entry point
├── start.sh / stop.sh             # Backend lifecycle
├── package.json                   # Playwright (browser e2e)
├── requirements.txt
├── AGENTS.md                      # Cursor/agent entry → init.md
├── init.md                        # Session protocol (repo root)
```

Runtime data: `~/.kb/` (see [storage.md](storage.md)). Not in the repo.

## Hotkeys (macOS app — ⌘⇧)

| Key | Action |
|---|---|
| `C` | Open chat |
| `G` | Open graph |
| `W` | Close main window |
| `S` | Screenshot capture |
| `I` | Flag screenshot as important |
| `P` | Proactive popup |

## Documentation

Start at [docs/README.md](README.md). Key references:

- [Configuration](configuration.md) — all env vars
- [Storage](storage.md) — `~/.kb/` layout
- [Constitution](constitution.md) — full engineering rules
