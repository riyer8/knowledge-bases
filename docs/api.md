# API Reference

Base URL: `http://127.0.0.1:8765`

## Endpoints

### `GET /health`

Returns service status and write path.

### `POST /chat`

JSON body:

```json
{
  "prompt": "user prompt string"
}
```

Uses `core/chat_prompt.txt` as the system prompt and calls the configured LLM (Claude when `CLAUDE_CODE_API_KEY` is set, otherwise fallback).

### `POST /manual-input`

JSON body:

```json
{
  "kind": "file | url | text",
  "value": "file path (for file) or raw content string",
  "createdAt": "ISO timestamp"
}
```

### `GET /manual-inputs`

Returns saved entries (newest first). The frontend manual log view renders oldest → newest and auto-scrolls to latest.

### `GET /graph`

Returns markdown graph nodes and edges. Query params:

- `orphans=1`
- `unlinked=1`
- `folder=<folder-prefix>`

### `POST /graph/dependency`

JSON body:

```json
{
  "source": "source node id/path",
  "target": "target node id/path"
}
```

Creates a manual dependency edge between two graph nodes.

### `POST /screenshot`

Captures the current screen and saves to `inputs/screenshot/captures/`.

### `POST /delete-all`

Deletes local runtime data:

- `inputs/manual/` (manual uploads + log)
- `inputs/.graph-dependencies.json`
- `inputs/screenshot/captures/`
- `~/.kb/pages/` (browser page contexts)

## Chrome Extension Endpoints

### `POST /page-context`

Ingest structured page representation from the Chrome extension.

JSON body: `url`, `title`, `site`, `headings`, `paragraphs`, `code_blocks`, `links`, `selected_text`, `page_type`, `visible_text`.

Returns `{ "ok": true, "page": { ... } }`.

### `POST /ask`

Ask a question about a page. Supports conversation history and streaming.

JSON body:

```json
{
  "question": "What does this mean?",
  "page_id": "uuid",
  "mode": "understand | connect | learn | explore",
  "history": [{"role": "user", "content": "..."}],
  "stream": true
}
```

When `stream: true`, returns Server-Sent Events with `{ "token": "..." }` chunks.

### `POST /remember`

Save a highlighted passage.

```json
{
  "page_id": "uuid",
  "selected_text": "highlighted text",
  "note": "optional note"
}
```

### `GET /search?q=...&top_k=8`

Semantic search over indexed reading history.

### `GET /connections?url=...&q=...&top_k=5`

Related prior reading for the current page or query.

### `GET /history?limit=20`

Recent page contexts captured by the extension.

### `GET /concepts?url=&q=&limit=50`

List or search the concept knowledge graph. When `url` or `q` is provided, returns related concepts for that page or query.

Returns concept nodes with `name`, `understanding_score`, `sources`, `related`, and `notes`.
