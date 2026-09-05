# Notes and bookshelf export

The **Notes editor** is the working UI. **Local drafts** (`chrome.storage.local`, canonical `pageDraft:<url>`) are the persistent store until you click **+ Save**. Library `quotes.json` is only for on-page highlight IDs. Library `pages/{id}.json` → `metadata.notes` is what Saved / graph / wiki / dashboard read after Save.

## Persistence (local-first)

| Action | Where notes live |
|---|---|
| Typing / highlighting | Side panel editor + flushed local draft |
| Panel close / tab switch | Local draft (flush on leave; not debounce-only) |
| Extension reload | Local draft restored by canonical URL |
| **+ Save** | Draft promoted into library `metadata.notes` (graph / wiki / dashboard) |

Draft keys use the same URL canonicalization as the library (strip hash, normalize trailing slash). Legacy exact-URL draft keys are migrated on read.

## Storage (document shape)

Page notes are markdown. Quote blocks are `>` blockquotes (or `:::quote` fences, which round-trip to the same document).

```markdown
> A passage from the article

Your commentary, with **bold** if you want.

> Another passage
```

`metadata.dateAdded` is `YYYY-MM-DD`, set once on first save and never overwritten on copy.

## Clipboard shape

Copy JSON produces a **JS object literal** (not `JSON.parse`-able) for pasting into a site:

```js
{
    title: "...",
    url: "...",
    author: "...",
    dateAdded: "2026-09-05",
    category: "...",
    medium: "...",
    tldr: "...",
    thoughts: "...",
    tags: ['tag'],
    notes: `:::quote
quoted text
:::

your commentary`
}
```

`notes` is `markdownBlockquotesToFences(editorMarkdown)`. Field names and `:::quote` fences are the contract.

Helpers live in `chrome-extension/sidepanel/notes.js`, `page-drafts.js`, and `bookshelf-export.js` (notes/export helpers are also under `web/` for the dashboard).
