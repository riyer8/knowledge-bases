# Architecture

## System Overview

A local-first macOS knowledge system. All data stays on device. External services are read-only
integrations (Calendar, Gmail, Slack) — they provide signal, they don't receive data.

```
┌─────────────────────────────────────────────────────┐
│                   macOS Desktop App                  │
│  (SwiftUI — hotkeys, menu bar, chat, graph, buckets) │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (localhost:8765)
┌──────────────────────▼──────────────────────────────┐
│                 Python Backend                        │
│                                                      │
│  ┌────────────┐  ┌───────────┐  ┌────────────────┐  │
│  │ Ingestion  │→ │  Privacy  │→ │    Memory      │  │
│  │            │  │ Pipeline  │  │  (index+graph) │  │
│  └────────────┘  └───────────┘  └───────┬────────┘  │
│                                          │            │
│  ┌───────────┐   ┌───────────┐  ┌───────▼────────┐  │
│  │Integrations│  │ Proactive │  │   Retrieval    │  │
│  │(GCal,Mail) │  │   Bot     │  │   (chat API)   │  │
│  └───────────┘  └───────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │   Local Storage  │
              │  ~/.kb/          │
              │  ├── events/     │
              │  ├── index/      │
              │  ├── graph/      │
              │  └── hashes/     │
              └─────────────────┘
```

---

## Module Descriptions

### core/ingestion/
Handles all data capture:
- Screen capture (with auto-pause triggers)
- Manual text/file/URL input
- Screenshot importance flagging
- Raw event emission (append-only log)

Output: raw events written to `~/.kb/events/raw/` (pre-privacy)

### core/privacy/
The mandatory gate between raw data and storage:
- Credential/password field detection → pause signal
- PII detection (names, emails, phone numbers)
- Name hashing (SHA-256 + salt, stored in `~/.kb/hashes/map.json`)
- Sensitivity scoring per event
- Banking/sensitive site detection

Output: sanitized events written to `~/.kb/events/clean/`

### core/memory/
Builds and maintains the knowledge graph:
- Chunking and embedding of clean events
- Graph edge detection (relationships between concepts, people-as-hashes, topics)
- Bucket classification (life buckets: health, work, relationships, learning, finances, etc.)
- Temporal indexing

Output: vector index at `~/.kb/index/`, graph at `~/.kb/graph/`

### core/retrieval/
Answers queries against the knowledge store:
- Semantic search over vector index
- Graph traversal for relationship queries
- Time-filtered retrieval
- Context assembly for LLM chat

### core/integrations/
Read-only connectors to external services:
- Google Calendar
- Gmail
- Slack
- Messages (iMessage)
- Health/fitness apps

Each integration emits events into the ingestion pipeline — same path as screen capture.

### core/proactive/
Detects patterns and surfaces insights unprompted:
- Pending item detection (unanswered messages, overdue tasks)
- Life balance pattern detection
- Relationship drift detection (haven't talked to X in N days)
- Trigger-based pop-ups to the frontend

### DesktopApp/ (Swift)
Five core UI functions:
1. **Chat** — conversational interface over the knowledge store
2. **Screen/Recording** — menu bar recording controls, importance flag
3. **Settings** — integrations, privacy controls, tone, relationship editing
4. **Proactive Bot** — scheduled pop-up surfacing insights
5. **Buckets of Life** — tree view of life categories, filterable by time/activity

---

## Data Flow

```
Raw Signal
   ↓
Ingestion (capture/collect)
   ↓
Privacy Pipeline (hash, redact, score) ← MANDATORY, cannot be bypassed
   ↓
Clean Event Log (append-only)
   ↓
Memory (embed, graph, bucket)
   ↓
Index + Graph
   ↓
Retrieval ← Chat queries here
   ↓
LLM (local via Ollama, or Claude API)
   ↓
Response
```

---

## LLM Strategy

- **Heavy processing** (chunking, embedding, relationship extraction): local model via Ollama
- **Chat interface**: Claude (highest quality for conversational responses)
- All LLM calls go through `core/llm_service.py` — never call APIs directly
- Model names are configured in `.env`, never hardcoded

---

## Storage Layout

```
~/.kb/
├── events/
│   ├── raw/          # pre-privacy (short TTL, deleted after processing)
│   └── clean/        # post-privacy (permanent, append-only)
├── index/            # vector embeddings
├── graph/            # knowledge graph edges
├── hashes/
│   └── map.json      # hash → display name mapping (never synced)
└── buckets/
    └── classifications.json
```

---

## API Endpoints (localhost:8765)

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Query the knowledge store |
| `/ingest` | POST | Manual input (text, file, URL) |
| `/graph` | GET | Return graph data for visualization |
| `/screenshot` | POST | Trigger screenshot capture |
| `/proactive` | GET | Get pending proactive insights |
| `/buckets` | GET | Return life bucket tree |
| `/health` | GET | Health check |
| `/delete-all` | POST | Full data reset (requires confirmation) |

---

## Phase Plan

See `ROADMAP.md` for the phased build plan.
Current phase status: see `STATE/architecture_state.md`.
