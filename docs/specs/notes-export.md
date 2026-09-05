# Notes and bookshelf export

The **Notes editor** is the source of truth for what you copy onto a personal site. Library `quotes.json` is only for on-page highlight IDs.

## Storage

Page `metadata.notes` is markdown. Quote blocks are `>` blockquotes (or `:::quote` fences, which round-trip to the same document).

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

Helpers live in `chrome-extension/sidepanel/notes.js` and `bookshelf-export.js` (copied to `web/` for the dashboard).
