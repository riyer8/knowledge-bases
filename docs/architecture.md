# Architecture

_Last updated: 2026-09-06_

A local-first personal knowledge system. All data stays on device. Multiple clients — Chrome
extension, local dashboard (`web/` at `/app/`), and macOS app — share one Python backend and one
storage root (`~/.kb/`).

## System Overview

```text
┌──────────────────────┐     ┌──────────────────────┐
│  Chrome Extension    │     │   macOS Desktop App   │
│  (page context,      │     │   (chat, library,     │
│   notes, library)    │     │    graph, pet, etc.)  │
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           │         ┌──────────────────┘
           │         │   web/ dashboard (/app/)
           └────┬────┘
                │ HTTP (localhost:8765)
   ┌────────────▼───────────────┐
   │      Python Backend          │
   │   core/frontend_backend.py   │
   │   + core/http/* route mixins │
   │                              │
   │  Ingestion → Privacy → Memory│
   │  Library / Wiki / Page ctx   │
   │  Retrieval + LLM providers   │
   └────────────┬─────────────────┘
                │
   ┌────────────▼────────────┐
   │   Local Storage         │
   │   ~/.kb/                │
   └─────────────────────────┘
```

**Separation of concerns:** clients capture context and render UI. The backend owns memory,
search, the concept graph, library, wiki, and all LLM calls. Never call external LLM APIs
outside `core/llm_service.py` / `core/llm_providers.py`.

## Clients

### Chrome Extension (`chrome-extension/`)

The browser is the primary reading surface. The extension:

- Extracts structured page context (title, URL, headings, selection, visible text, metadata)
- Provides unified chat about the current page (`POST /ask`)
- Saves pages and quotes explicitly (`/library/*`). The Notes document (`metadata.notes`) is the export source of truth; Copy JSON emits the current JS object with `:::quote` fences.
- **Page | Saved | Graph** tabs plus **Settings** (gear). Life and Wiki are archived from nav (APIs remain).
- Page sub-panels: **Details | Notes | Chat** (default: Details)
- On-page highlight toolbar for fast quote capture (available even if the panel is closed)
- PDF text extract via `POST /library/extract-document`
- Visualizes a page-centric knowledge graph (saved pages linked by shared topics)

The extension does **not** contain the knowledge brain — it sends context to the backend.

### Local dashboard (`web/`)

Static UI served by the backend at `http://127.0.0.1:8765/app/`. Library notes + Copy JSON match
the extension. Life/Wiki views exist in the tree but are archived from nav (see [archived.md](archived.md)).

### macOS Desktop App (`DesktopApp/`)

Swift/SwiftUI app (**Context.app**) with menu bar, desktop pet, chat, **library**, **life** panel,
**wiki** panel, graph view, manual inputs, screenshots, proactive insights, and settings.
Connects to the same backend at `http://127.0.0.1:8765`.

Library on desktop is still pages/quotes-oriented (notes document parity is a follow-on). Proactive
insights surface via the macOS pet / `⌘⇧P` popup (`GET /proactive`). There is no extension proactive banner today.

**Intentional split:** desktop chat uses memory-wide `POST /chat`; extension uses streaming
`POST /ask` with page context. Both are supported.

Install: `bash scripts/install_app.sh`

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
After privacy processing, `event_writer` appends raw and clean events under `~/.kb/events/`.

### `core/privacy/`

Mandatory gate between raw data and storage:

- Credential/password field detection → pause signal
- PII detection (names, emails, phone numbers)
- Name hashing (SHA-256 + salt, stored in `~/.kb/hashes/map.json`)
- Sensitivity scoring and banking/sensitive site detection

Returns a sanitized event dict; **ingestion** writes clean events to disk.

### `core/memory/`

Chunking, embeddings, vector store, bucket classification, graph edges, concept graph,
buckets service, and relationship profiles (`relationships.py` → `~/.kb/relationships/`).

### `core/library_service.py` + `core/page_context_service.py`

Extension-facing services:

- **Page context** — ingest, search, connections, remember passages
- **Saved library** — explicit page saves, quotes, notes metadata, PDF extract, per-page chat, explore

### `core/wiki_service.py`

Markdown wiki under `~/.kb/wiki/`: raw ingest, LLM compile into linked articles, search, ask.

### `core/retrieval/`

Semantic search, context assembly (hash→name rendering via `context_assembler.render_response`),
RAG chat (`chat.py`), and page-aware chat (`ask_about_page` in `page_chat.py`).

### `core/integrations/`

Read-only connectors (Google Calendar, Gmail, iMessage). Each emits events into the ingestion pipeline.

### `core/proactive/`

Pattern detection and ranked insights. Consumed by the desktop pet / proactive popup today.

### `core/http/` + `core/env_settings.py`

HTTP route mixins (library, buckets, relationships, wiki, static `/app/`) and `.env` settings
read/write for `GET`/`POST /settings`.

### `core/llm_providers.py`

Provider abstraction: OpenAI, Anthropic, Ollama. `KB_LLM_PROVIDER=auto` uses OpenAI when
`OPENAI_API_KEY` is set, otherwise Ollama. Embeddings: Ollama or OpenAI (`KB_EMBED_PROVIDER`).

## Data Flow

```text
Raw signal (screen, page, manual input, integration)
        ↓
Ingestion
        ↓
Privacy pipeline (hash, redact, score)  ← mandatory, cannot be bypassed
        ↓
Clean event log (ingestion writes) + library + page context + wiki
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

All runtime data lives under `~/.kb/` (configured via `KB_ROOT`). Full map: [storage.md](storage.md).

```text
~/.kb/
├── library/              # saved pages, quotes, notes, per-page chat
├── wiki/                 # raw sources + compiled articles
├── pages/                # ephemeral page context from extension capture
├── events/
│   ├── raw/
│   ├── clean/
│   └── paused.log
├── index/
├── graph/                # edges.json + concepts.json
├── relationships/        # profiles.json
├── hashes/               # map.json + salt
├── buckets/
└── auth/                 # OAuth tokens
```

Use `POST /library/clear` or `POST /delete-all` to reset runtime data (`delete-all` also clears
wiki and relationships).

## API Surface

Base URL: `http://127.0.0.1:8765`. Full reference: [api.md](api.md).

| Area | Key endpoints |
|---|---|
| Health | `GET /health` |
| Extension chat | `POST /ask`, `POST /page-context`, `POST /remember` |
| Saved library | `GET/POST /library/pages`, `/library/quotes`, `/library/graph`, `/library/explore`, `POST /library/extract-document` |
| Search & memory | `GET /search`, `GET /connections`, `GET /history`, `GET /concepts` |
| Desktop | `POST /chat`, `GET /graph`, `POST /screenshot`, `GET /proactive`, `GET /settings` |
| Life buckets | `GET /buckets/*`, `GET /dashboard/time`, `POST /buckets/override` |
| Relationships | `GET/POST /relationships/*` |
| Wiki | `GET/POST /wiki/*` (archived from nav; APIs live) |
| Manual input | `POST /manual-input`, `GET /manual-inputs` |
| Integrations | `GET /integrations/status`, GCal/Gmail OAuth, `POST /integrations/imessage/sync` |
| Dashboard | `GET /app`, `GET /app/*` → `web/` |
| Reset | `POST /delete-all`, `POST /library/clear` |

## LLM Strategy

- **Chat + page Q&A:** configured provider via `KB_LLM_PROVIDER` (auto-detects OpenAI)
- **Embeddings:** `KB_EMBED_PROVIDER` (auto uses OpenAI when key is set; Anthropic has no embed path)
- All calls go through `core/llm_providers.py` — never call APIs directly
- Model names live in `.env`, never hardcoded

## Repo Layout

```text
knowledge-bases/
├── core/                 # Python backend
├── web/                  # Local dashboard (served at /app/)
├── chrome-extension/     # Chrome side panel + launcher client
├── DesktopApp/           # macOS SwiftUI app
├── docs/                 # product + developer documentation
├── tests/
├── scripts/              # start_backend, launcher, e2e, install/build
├── demo/
├── main.py
├── start.sh / stop.sh
├── package.json          # Playwright for browser e2e
├── AGENTS.md             # Cursor/agent entry → init.md
├── init.md               # session protocol
```

### Future extraction (not started)

Over time, shared logic may move from `core/` into a `backend/` package. Do not refactor
until both clients are stable on the current API.

## Dependency Graph

```text
Clients (extension, web/, DesktopApp)
        → frontend_backend.py + core/http/*
        → retrieval | proactive | ingestion | library | wiki | page_context
        → privacy (mandatory for ingestion)
        → memory (+ relationships, buckets)
        → llm_providers / llm_service
```

Before changing a module, check what depends on it. Cross-module interface changes require a
new entry in `docs/decisions.md`.

## Related Docs

- [Overview](overview.md)
- [Configuration](configuration.md)
- [Storage](storage.md)
- [API Reference](api.md)
- [Getting Started](getting-started.md)
- [Roadmap](roadmap.md)
- [Project Structure](project-structure.md)
- [Vision](vision.md)
- [Constitution](constitution.md)
