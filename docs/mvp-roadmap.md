# MVP Roadmap

## Completed — Chrome Extension MVP

### Day 1 — Core Loop

- Open side panel, read current webpage
- Extract title, URL, visible text, headings, selection
- Send to Python backend, stream LLM answer back
- Endpoints: `POST /page-context`, `POST /ask`

### Day 2 — Conversation Context

Follow-up questions keep page + thread context in the side panel (`history` in `POST /ask`).

### Day 3 — Auto-Save

Pages persisted on context capture; interactions increment via `/ask` and `/remember`.

### Day 4 — Semantic Search

`GET /search?q=` searches indexed reading history.

### Day 5 — Connections

`GET /connections` surfaces related prior reading for the current page.

### Day 6+ — Knowledge Graph

Concept nodes with sources, relationships, and understanding scores.
See `core/memory/concept_graph.py` and `GET /concepts`.

### UX Polish

- Floating "+ Remember" on text selection
- Live selection in side panel
- Unified chat (no mode tabs)
- Saved library with quotes, explore suggestions, and graph visualization

## Side Panel Target UX

```text
┌─────────────────────────────┐
│ ✨ Context                  │
│                             │
│ Scaling Laws for Neural     │
│ Language Models             │
│                             │
│ ─────────────────────────── │
│                             │
│ Ask anything...             │
│                             │
│ ─────────────────────────── │
│                             │
│ 💡 Connected to             │
│                             │
│ • Attention Is All You Need │
│ • Chinchilla                │
│ • Your notes on transformers│
│                             │
└─────────────────────────────┘
```

## API Endpoints (implemented)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/page-context` | Ingest structured page representation |
| `POST` | `/ask` | Ask a question with page + memory context |
| `POST` | `/remember` | Save a highlighted passage as a concept |
| `GET` | `/concepts` | Concept knowledge graph |
| `GET` | `/search` | Semantic search over reading history |
| `GET` | `/connections` | Related concepts + prior reading |
| `GET` | `/history` | Recent reading history |
| `POST` | `/library/save-page` | Explicitly save a page + summary |
| `GET` | `/library/pages` | List saved pages |
| `GET` | `/library/pages/{id}` | Saved page detail + chat + quotes |
| `DELETE` | `/library/pages/{id}` | Clear memory for one page |
| `POST` | `/library/quotes` | Save an individual quote |
| `GET` | `/library/quotes` | List quotes |
| `POST` | `/library/explore` | Sparkles suggestions |
| `GET` | `/library/graph` | Graph nodes + edges for visualization |
| `POST` | `/library/clear` | Wipe all stored data |

## Next — macOS App Integration

- Surface saved library in `DesktopApp/` (`/library/*`)
- Unify desktop chat on `POST /ask` (same as extension)
- Proactive "you've read this before" popups using `/connections`

## Future (not started)

- Repo-wide refactor into `backend/` package
- Safari extension
- Proactive insights in browser (not just desktop)
