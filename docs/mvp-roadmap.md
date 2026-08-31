# MVP Roadmap

## Day 1 — Core Loop ✅

Chrome extension can:

- Open side panel
- Read current webpage
- Extract: title, URL, visible text, headings, current selection
- Send it to Python backend
- Ask configured LLM (Ollama/OpenAI/Anthropic)
- Stream answer back

Implemented in `chrome-extension/` with backend endpoints `POST /page-context` and `POST /ask`.

## Day 2 — Conversation Context ✅

Follow-up questions keep page + thread context in the side panel (`history` in `POST /ask`).

## Day 3 — Auto-Save ✅

Pages are persisted on context capture; interactions increment via `/ask` and `/remember`.

## Day 4 — Semantic Search ✅

`GET /search?q=` searches indexed reading history.

## Day 5 — Connections ✅

`GET /connections` surfaces related prior reading for the current page.

## Day 6+ — Knowledge Graph

Build the actual concept graph with sources, relationships, and understanding scores.

Side panel mockup:

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

## Day 2 — Conversation Context

```text
Page → Question → Answer → Follow-up
```

## Day 3 — Auto-Save

Automatically save pages you've meaningfully interacted with.

## Day 4 — Semantic Search

Search over previous pages. "Have I seen this before?" works.

## Day 5 — Connections

```text
Current page → Relevant things you've read → LLM explains relationship
```

## Day 6+ — Knowledge Graph ✅

Concept nodes with sources, relationships, and understanding scores. See `core/memory/concept_graph.py` and `GET /concepts`.

## UX Polish ✅

- Floating "+ Remember" on text selection
- Live selection in side panel
- Suggested questions per mode
- Concept + reading badges in connections

## API Endpoints (all implemented)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/page-context` | Ingest structured page representation |
| `POST` | `/ask` | Ask a question with page + memory context |
| `POST` | `/remember` | Save a highlighted passage as a concept |
| `GET` | `/concepts` | Concept knowledge graph |
| `GET` | `/search` | Semantic search over reading history |
| `GET` | `/connections` | Related concepts + prior reading |
| `GET` | `/history` | Recent reading history |

## Future (not started)

- Repo-wide refactor into `backend/`
- Major changes to the macOS app
- Proactive "you've read this before" popups in desktop app
