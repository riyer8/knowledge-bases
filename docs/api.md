# API Reference

_Last updated: 2026-09-06_

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
Requires either a full `page` object **or** `saved_page_id` (loads the saved library page).

```json
{
  "question": "What does this mean?",
  "page": {
    "url": "...",
    "title": "...",
    "visible_text": "..."
  },
  "saved_page_id": "optional-library-id",
  "history": [{"role": "user", "content": "..."}],
  "stream": true
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

### `PATCH /library/pages/{id}`

Update a saved page's title and/or metadata.

```json
{
  "title": "New title",
  "metadata": {
    "author": "...",
    "date": "...",
    "category": "...",
    "medium": "...",
    "tldr": "...",
    "thoughts": "...",
    "notes": "...",
    "dateAdded": "2026-09-05",
    "tags": ["scaling"],
    "custom": [{"key": "Journal", "value": "..."}]
  }
}
```

At least one of `title` or `metadata` is required. Metadata is normalized to the fields above
(`notes` is the Notes / bookshelf export document).

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

### `PATCH /library/quotes/{id}`

Update quote text and/or note. At least one field required.

```json
{ "text": "updated passage", "note": "optional note" }
```

### `DELETE /library/quotes/{id}`

Delete a single quote.

### `POST /library/explore`

AI-suggested things to explore next for a page.

```json
{ "page": { "url": "...", "title": "..." } }
```

Returns `{ "suggestions": [...] }`.

### `POST /library/extract-document`

Extract text from a PDF (or similar) for library save / page context. Used by the extension
when reading `file://` / PDF tabs.

```json
{
  "url": "file:///…/paper.pdf",
  "content_base64": "<base64 PDF bytes>",
  "title": "optional title"
}
```

Returns `{ "ok": true, "page": { ... } }` with extracted text and metadata when available.

### `GET /library/graph`

Page-centric graph for the extension: **saved pages only**, with edges when pages share
topics from highlighted quotes (individual quotes are not separate nodes).

### `POST /library/clear`

Clears the saved library only (pages, quotes, per-page chats). Returns
`{ "ok": true, "scope": "library" }`.

## Settings (all clients)

### `GET /settings`

Runtime settings: LLM provider, models, env file path, masked API key hints, setup notes.

### `POST /settings`

Update repo `.env` (extension Settings panel or API). Supported fields:

```json
{
  "llm_provider": "auto | openai | ollama | anthropic",
  "openai_api_key": "sk-...",
  "anthropic_api_key": "sk-ant-...",
  "openai_model": "gpt-4o-mini",
  "chat_model": "qwen2.5:3b",
  "embed_provider": "auto | ollama | openai",
  "proactive_interval_minutes": 20
}
```

Omitted API key fields leave existing keys unchanged.

## Wiki (APIs live; archived from nav)

LLM-maintained markdown wiki at `~/.kb/wiki/`. Raw sources in `wiki/raw/` are compiled into
linked articles in `wiki/articles/`. Extension and dashboard hide Wiki from primary nav
([archived.md](archived.md)); Desktop still exposes a Wiki panel. Dashboard shell:
`http://127.0.0.1:8765/app/`.

### `GET /wiki/status`

Counts of raw sources, articles, and pending compile jobs.

### `GET /wiki/index`

Returns `{ "index": "..." }` — the auto-maintained `index.md` contents.

### `GET /wiki/raw` · `GET /wiki/raw/{id}`

List or fetch raw source documents.

### `GET /wiki/articles` · `GET /wiki/articles/{slug}`

List or fetch compiled wiki articles.

### `GET /wiki/search?q=...`

Full-text search across raw sources and articles.

### `POST /wiki/ingest`

Add a source. Either pass `page_id` (saved library page) or `title` + `content`:

```json
{ "page_id": "abc123" }
```

### `POST /wiki/compile`

Incrementally compile unprocessed raw sources into articles (LLM). Body: `{ "max_sources": 3 }`.

### `POST /wiki/health-check`

LLM review of wiki consistency — returns issues, suggestions, and new article ideas.

### `POST /wiki/ask`

Q&A over the compiled wiki. Sends relevant articles + index as context to the LLM.

```json
{ "question": "How do my notes on scaling laws connect?", "history": [] }
```

Returns `{ "ok": true, "reply": "...", "sources": ["Article Title", ...] }`.

## Desktop App — Chat & inputs

### `POST /chat`

General knowledge-store chat (desktop app). Supports conversation history and calendar context.

```json
{
  "prompt": "user prompt string",
  "history": [{"role": "user", "content": "..."}],
  "include_calendar": true
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

Returns pending proactive insights for the macOS pet / proactive popup. (No extension banner UI today.)

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

Deletes runtime data under `~/.kb/`: library, events (incl. `paused.log`), index, graph,
hashes, buckets, pages, wiki, relationships, and OAuth tokens under `auth/`. Returns
`{ "ok": true, "scope": "all" }`.

### `POST /ingest`

Direct text ingestion (internal/testing).
