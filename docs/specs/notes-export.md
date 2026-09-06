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

Page notes are a markdown subset: paragraphs, `>` blockquotes, `#`–`###` headings, `-` / `1.` lists, and inline `**bold**` `*italic*` `` `code` `` links. `:::quote` fences round-trip to the same `>` document.

```markdown
> A passage from the article

Your commentary, with **bold** if you want.

> Another passage
```

### Quotes in the editor

| Action | Behavior |
|---|---|
| Page highlight | Inserts a linked blockquote + library quote + page paint |
| Type `> ` at the start of a line | Converts that paragraph into an **unlinked** blockquote (notes + export only; no page paint) |
| Enter inside a quote | New paragraph inside the quote |
| Enter on an empty quote line | Exit the quote (commentary paragraph after) |
| × on a linked quote | Removes the block and the library/highlight record |
| × on a manual quote | Removes the block only |

`metadata.dateAdded` is `YYYY-MM-DD`, set once on first save and never overwritten on copy.

Titles are single-line: newlines / excess whitespace are collapsed on load, blur, and draft save.

## Clipboard shape

Copy JSON produces a **JS object literal** (not `JSON.parse`-able) for pasting into a site.

Matches site `BookshelfPage/data/*.js` (e.g. essayData / researchPaperData):

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
    notes: `
:::quote
quoted text
:::

your commentary
`
}
```

Quotes use `:::quote` … `:::`. Your commentary stays outside the fences. The Notes tab editor keeps `>` / HTML blockquotes internally; export reads the DOM via `domToExportNotes`.

Helpers live in `chrome-extension/sidepanel/notes.js`, `page-drafts.js`, and `bookshelf-export.js` (notes/export helpers are also under `web/` for the dashboard).
