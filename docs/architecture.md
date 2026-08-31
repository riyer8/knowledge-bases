# Architecture

## Target System

```text
                    CHROME
                       │
              ┌────────▼────────┐
              │   Side Panel    │
              │                 │
              │  Ask anything   │
              │  about page     │
              └────────┬────────┘
                       │
              Current page context
                       │
                       ▼
              ┌─────────────────┐
              │ Context Engine  │
              │                 │
              │ DOM             │
              │ URL             │
              │ title           │
              │ selection       │
              │ metadata        │
              │ page structure  │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Knowledge       │
              │ Engine          │
              │                 │
              │ embeddings      │
              │ chunks          │
              │ entities        │
              │ relationships   │
              │ history         │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │      LLM        │
              │  OpenAI / etc.  │
              └─────────────────┘
```

## Structured Page Representation

Don't just send the webpage to the LLM. The extension creates a structured representation:

```json
{
  "url": "...",
  "title": "...",
  "site": "arxiv.org",
  "headings": [],
  "paragraphs": [],
  "code_blocks": [],
  "links": [],
  "images": [],
  "tables": [],
  "selected_text": "...",
  "page_type": "research_paper"
}
```

When the user asks "How does this compare to what I read yesterday?":

```text
Current page
        +
Recent reading history
        +
Semantic search over knowledge base
        +
User's question
        ↓
      LLM
```

## Repo Evolution

Build on the existing repo — don't start a separate one. The Python backend already has the most valuable part: the memory/knowledge engine. The Chrome extension becomes a new interface into that brain.

### Before

```text
Knowledge Bases
│
├── macOS App
│   ├── Desktop Pet
│   ├── Assistant UI
│   ├── Chat
│   └── Graph
│
└── Python Backend
    ├── Chat
    ├── Knowledge
    ├── Graph
    ├── Screenshots
    └── Storage
```

### After

```text
Personal Knowledge Engine
│
├── Interfaces
│   │
│   ├── Chrome Extension      ← NEW
│   │   ├── Side Panel
│   │   ├── Page Context
│   │   └── "Remember this"
│   │
│   └── macOS App             ← EXISTING
│       ├── Desktop Pet
│       ├── Assistant
│       └── Graph
│
└── Core / Backend
    ├── Memory
    ├── Knowledge Graph
    ├── Semantic Search
    ├── LLM
    ├── Page Ingestion
    └── Storage
```

### Target Directory Layout

```text
knowledge-bases/
│
├── backend/              # extracted over time from core/
│   ├── api/
│   ├── memory/
│   ├── knowledge/
│   ├── llm/
│   ├── storage/
│   └── ingestion/
│
├── chrome-extension/     # NEW — add first, don't refactor yet
│   ├── manifest.json
│   ├── sidepanel/
│   ├── content/
│   ├── background/
│   └── components/
│
├── desktop/
│   └── DesktopApp/
│
├── data/
│
└── README.md
```

## Separation of Concerns

The Chrome extension should not contain the knowledge brain. It captures context and says: "Hey backend, here's what I'm looking at."

```text
             ┌── Chrome
             │
             ├── macOS
             │
             └── future clients
                    │
                    ▼
             Personal Memory
                    │
             ┌──────┼──────┐
             ▼      ▼      ▼
           Search  Graph   LLM
```

## Feature Mapping (Old → New)

| Current feature | Future |
|---|---|
| Chat | Shared LLM/chat engine |
| Manual URLs | Automatic webpage ingestion |
| Manual text | Highlight → Remember |
| Markdown graph | Personal knowledge graph |
| Screenshots | Future browser screenshot/context |
| Graph View | Mac app + eventually web UI |
| Desktop pet | Still exists |
| Local storage | Still exists |
| Claude | LLM provider (one of many) |
| OpenAI | Add as another provider |
| ProactivePopup | "You've read something related to this before" |

## LLM Provider Abstraction

Replace Claude-specific chat with a provider abstraction:

```text
LLMProvider
    ├── OpenAI
    ├── Anthropic
    └── Local (Ollama)
```

## Phase 1 Strategy

Don't rewrite the old code yet. Add `chrome-extension/` and make it talk to the existing `localhost:8765` backend:

```text
Open webpage → Click extension → Side panel opens
      → Extract page → POST /page-context
      → Ask question → POST /chat → Answer
```

Once the extension works, extract shared logic into `backend/knowledge/`, `backend/memory/`, `backend/search/`, `backend/llm/`, and `backend/ingestion/` — then both clients use it.

See [MVP Roadmap](mvp-roadmap.md) for the day-by-day plan.
