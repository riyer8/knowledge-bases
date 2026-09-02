# API Reference

Base URL: `http://127.0.0.1:8765`

All endpoints accept and return JSON unless noted. CORS headers are set for the Chrome
extension.

## Health

### `GET /health`

Returns service status and storage path.

## Chrome Extension — Page Context & Chat

### `POST /page-context`

Ingest structured page representation from the Chrome extension.

JSON body: `url`, `title`, `site`, `headings`, `paragraphs`, `code_blocks`, `links`,
`selected_text`, `page_type`, `visible_text`.

Returns `{ "ok": true, "page": { ... } }`.

### `POST /ask`

Ask a question about a page. Supports conversation history and streaming.

```json
{
  "question": "What does this mean?",
  "page_id": "uuid",
  "history": [{"role": "user", "content": "..."}],
  "stream": true,
  "saved_page_id": "optional-library-id"
}
```

When `stream: true`, returns Server-Sent Events with `{ "token": "..." }` chunks.

### `POST /remember`

Save a highlighted passage as a concept.

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

List or search the concept knowledge graph.

## Saved Library

### `GET /library/pages?limit=100`

List saved pages (newest first).

### `GET /library/pages/{id}`

Saved page detail including chat history and quotes.

### `DELETE /library/pages/{id}`

Delete a saved page and its associated memory.

### `GET /library/by-url?url=...`

Look up a saved page by URL.

### `POST /library/save-page`

Explicitly save a page with summary.

```json
{
  "page": { "url": "...", "title": "...", "summary": "..." },
  "history": [{"role": "user", "content": "..."}]
}
```

### `POST /library/quotes`

Save an individual quote.

```json
{
  "text": "quoted passage",
  "page_id": "optional",
  "page_url": "...",
  "page_title": "...",
  "note": "optional"
}
```

### `GET /library/quotes?page_id=&page_url=`

List quotes, optionally filtered by page.

### `POST /library/explore`

AI-suggested things to explore next for a page.

```json
{ "page": { "url": "...", "title": "..." } }
```

Returns `{ "suggestions": [...] }`.

### `GET /library/graph`

Graph nodes and edges for the saved library visualization.

### `POST /library/clear`

Wipe all library data (saved pages, quotes, chats).

## Desktop App — Legacy Endpoints

### `POST /chat`

General knowledge-store chat (desktop app). Supports conversation history and calendar context.

```json
{
  "prompt": "user prompt string",
  "history": [{"role": "user", "content": "..."}],
  "include_calendar": true
}
```

### `GET /settings`

Runtime settings for clients (proactive cadence, model info).

```json
{
  "proactive_interval_minutes": 20,
  "chat_model": "qwen2.5:3b",
  "llm_provider": "ollama"
}
```

### `POST /manual-input`

```json
{
  "kind": "file | url | text",
  "value": "file path (for file) or raw content string",
  "createdAt": "ISO timestamp"
}
```

### `GET /manual-inputs`

Returns saved manual input entries (newest first).

### `GET /graph`

Returns markdown graph nodes and edges. Query params: `orphans=1`, `unlinked=1`,
`folder=<folder-prefix>`.

### `POST /graph/dependency`

```json
{
  "source": "source node id/path",
  "target": "target node id/path"
}
```

### `POST /screenshot`

Captures the current screen and runs it through the ingestion pipeline.

```json
{ "flaggedImportant": true }
```

Set `flaggedImportant` to mark the moment as high-priority in retrieval.

### `GET /proactive`

Returns pending proactive insights for the desktop app and extension banner.

### `GET /dashboard/time?days=7`

Life-bucket time breakdown for the "how I spend my time" dashboard.

### `GET /buckets`

Returns life bucket classifications map.

### `GET /buckets/taxonomy`

Bucket tree and flat leaf list.

### `GET /buckets/summary?days=7`

Event counts per bucket over the last N days.

### `GET /buckets/tree?days=7`

Grouped bucket view for UI tree filters.

### `GET /buckets/events?bucket=Work/Meetings&days=7`

Recent events in a bucket.

### `GET /buckets/recent?days=7&limit=30`

Recent classified events across all buckets (for review UIs).

### `POST /buckets/override`

```json
{ "event_id": "uuid", "bucket": "Work/Meetings" }
```

### `GET /relationships`

List relationship profiles (from person graph + hash map).

### `GET /relationships/{person_hash}`

Single profile with graph connections.

### `POST /relationships/{person_hash}`

```json
{ "display_name": "Alice", "notes": "Met at conference" }
```

## Integrations

### `GET /integrations/status`

OAuth connection status for GCal and Gmail.

### `GET /integrations/gcal/auth` / `GET /integrations/gmail/auth`

Start OAuth flow.

### `GET /integrations/gcal/callback` / `GET /integrations/gmail/callback`

OAuth callback handlers.

### `POST /integrations/gcal/sync` / `POST /integrations/gmail/sync`

Trigger a sync.

### `GET /integrations/pending`

Pending integration items.

### `GET /integrations/imessage/status`

Whether iMessage `chat.db` is readable on this Mac.

### `POST /integrations/imessage/sync`

```json
{ "limit": 20 }
```

Ingest recent iMessages through the privacy pipeline.

## Data Reset

### `POST /delete-all`

Deletes all runtime data under `~/.kb/` (library, events, index, graph, hashes, buckets,
pages).

### `POST /ingest`

Direct text ingestion (internal/testing).
