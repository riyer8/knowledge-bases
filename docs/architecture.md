# Architecture

A local-first personal knowledge system. All data stays on device. Multiple clients — Chrome
extension and macOS app — share one Python backend and one storage root (`~/.kb/`).

## System Overview

```text
┌──────────────────────┐     ┌──────────────────────┐
│  Chrome Extension    │     │   macOS Desktop App   │
│  (page context,      │     │   (chat, graph, pet,  │
│   saved library)     │     │    screenshots, etc.) │
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           └────────────┬───────────────┘
                        │ HTTP (localhost:8765)
           ┌────────────▼───────────────┐
           │      Python Backend          │
           │   core/frontend_backend.py   │
           │                              │
           │  ┌──────────┐  ┌──────────┐  │
           │  │ Ingestion│→ │ Privacy  │  │
           │  └────┬─────┘  └────┬─────┘  │
           │       │             │        │
           │  ┌────▼─────────────▼─────┐  │
           │  │ Memory + Library       │  │
           │  │ (index, graph, pages)  │  │
           │  └───────────┬────────────┘  │
           │              │               │
           │  ┌───────────▼────────────┐  │
           │  │ Retrieval + LLM        │  │
           │  └────────────────────────┘  │
           └────────────┬─────────────────┘
                        │
           ┌────────────▼────────────┐
           │   Local Storage         │
           │   ~/.kb/                │
           └─────────────────────────┘
```

**Separation of concerns:** clients capture context and render UI. The backend owns memory,
search, the concept graph, and all LLM calls. Never call external LLM APIs outside
`core/llm_service.py` / `core/llm_providers.py`.

## Clients

### Chrome Extension (`chrome-extension/`)

The browser is the primary reading surface. The extension:

- Extracts structured page context (title, URL, headings, selection, visible text)
- Provides unified chat about the current page (`POST /ask`)
- Saves pages and quotes explicitly (`/library/*`)
- Visualizes the concept graph in the side panel

The extension does **not** contain the knowledge brain — it sends context to the backend.

### macOS Desktop App (`DesktopApp/`)

Swift/SwiftUI app with hotkeys, desktop pet, chat, graph view, manual inputs, screenshots,
and proactive insights. Connects to the same backend at `http://127.0.0.1:8765`.

**Current gap:** the desktop app uses legacy endpoints (`/chat`, `/graph`, `/screenshot`,
`/proactive`). The extension's saved library (`/library/*`) and page-context chat (`/ask`)
are not yet surfaced in the macOS UI. Both clients already share the same `~/.kb/` storage —
wiring the desktop app to `/library/*` is the next integration step.

### Future clients

Safari extension, PDF reader, terminal, phone — all feed the same backend. Do not start a
separate repo; add interfaces here.

## Structured Page Representation

The extension sends structured context, not raw HTML:

```json
{
  "url": "...",
  "title": "...",
  "site": "arxiv.org",
  "headings": [],
  "paragraphs": [],
  "code_blocks": [],
  "links": [],
  "selected_text": "...",
  "page_type": "research_paper",
  "visible_text": "..."
}
```

When the user asks "How does this compare to what I read yesterday?":

```text
Current page + recent reading history + semantic search + user question → LLM
```

## Module Descriptions

### `core/ingestion/`

Handles data capture: screenshots (with OCR), manual text/file/URL input, and page context.
Output flows through the privacy pipeline before storage.

### `core/privacy/`

Mandatory gate between raw data and storage:

- Credential/password field detection → pause signal
- PII detection (names, emails, phone numbers)
- Name hashing (SHA-256 + salt, stored in `~/.kb/hashes/map.json`)
- Sensitivity scoring and banking/sensitive site detection

Output: sanitized events in `~/.kb/events/clean/`

### `core/memory/`

Chunking, embeddings, vector store, bucket classification, and graph edges.
Includes `concept_graph.py` for the extension's knowledge graph.

### `core/library_service.py` + `core/page_context_service.py`

Extension-facing services:

- **Page context** — ingest, search, connections, remember passages
- **Saved library** — explicit page saves, quotes, per-page chat history, explore suggestions

### `core/retrieval/`

Semantic search, context assembly (hash→name rendering), RAG chat (`chat.py`), and
page-aware chat (`page_chat.py`).

### `core/integrations/`

Read-only connectors (Google Calendar, Gmail). Each emits events into the ingestion pipeline.

### `core/proactive/`

Pattern detection and ranked insights surfaced to the desktop app.

### `core/llm_providers.py`

Provider abstraction: OpenAI, Anthropic, Ollama. `KB_LLM_PROVIDER=auto` uses OpenAI when
`OPENAI_API_KEY` is set, otherwise Ollama.

## Data Flow

```text
Raw signal (screen, page, manual input, integration)
        ↓
Ingestion
        ↓
Privacy pipeline (hash, redact, score)  ← mandatory, cannot be bypassed
        ↓
Clean event log + library + page context
        ↓
Memory (embed, graph, bucket)
        ↓
Index + graph
        ↓
Retrieval ← chat queries here
        ↓
LLM (OpenAI / Anthropic / Ollama)
        ↓
Response
```

## Storage Layout

All runtime data lives under `~/.kb/` (configured via `KB_ROOT`):

```text
~/.kb/
├── library/              # saved pages, quotes, per-page chat (extension)
│   ├── saved_pages.json
│   ├── pages/
│   ├── chats/
│   └── quotes.json
├── pages/                # ephemeral page context from extension capture
├── events/
│   ├── raw/              # pre-privacy (short TTL)
│   └── clean/            # post-privacy (append-only)
├── index/                # vector embeddings
├── graph/                # knowledge graph + concepts.json
├── hashes/
│   └── map.json          # hash → display name (never synced)
└── buckets/
    └── classifications.json
```

Use `POST /library/clear` or `POST /delete-all` to reset runtime data.

## API Surface

Base URL: `http://127.0.0.1:8765`. Full reference: [api.md](api.md).

| Area | Key endpoints |
|---|---|
| Health | `GET /health` |
| Extension chat | `POST /ask`, `POST /page-context`, `POST /remember` |
| Saved library | `GET/POST /library/pages`, `/library/quotes`, `/library/graph`, `/library/explore` |
| Search & memory | `GET /search`, `GET /connections`, `GET /history`, `GET /concepts` |
| Desktop (legacy) | `POST /chat`, `GET /graph`, `POST /screenshot`, `GET /proactive` |
| Manual input | `POST /manual-input`, `GET /manual-inputs` |
| Integrations | `GET /integrations/status`, sync + OAuth callbacks |
| Reset | `POST /delete-all`, `POST /library/clear` |

## LLM Strategy

- **Chat + page Q&A:** configured provider via `KB_LLM_PROVIDER` (auto-detects OpenAI)
- **Embeddings:** `KB_EMBED_PROVIDER` (auto uses OpenAI when key is set)
- All calls go through `core/llm_providers.py` — never call APIs directly
- Model names live in `.env`, never hardcoded

## Repo Layout

```text
knowledge-bases/
├── core/                 # Python backend (memory, retrieval, privacy, ingestion)
├── chrome-extension/     # Chrome side panel + HTTP launcher
├── DesktopApp/           # macOS SwiftUI app
├── docs/                 # product + developer documentation
├── tests/
├── scripts/start_backend.sh
├── main.py               # backend launcher
├── CLAUDE.md             # engineering constitution
└── init.md               # AI session protocol
```

### Future extraction (not started)

Over time, shared logic may move from `core/` into a `backend/` package. Do not refactor
until both clients are stable on the current API.

## Dependency Graph

Before changing a module, check:

- What does it depend on?
- What depends on it?
- What is the blast radius if the interface changes?

Cross-module interface changes require a new entry in `docs/decisions.md`.

## Related Docs

- [Overview](overview.md)
- [API Reference](api.md)
- [Getting Started](getting-started.md)
- [Roadmap](roadmap.md)
- [Project Structure](project-structure.md)
- [Vision](vision.md)
