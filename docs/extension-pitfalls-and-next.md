# Chrome extension — pending pitfalls and next work

_Last updated: 2026-09-06_

**Purpose:** Detailed backlog of remaining Chrome extension risks and product gaps after extension **0.1.8** and Phase 2 (backend title normalize + Playwright smoke). **Do not treat this as an implementation ticket** — it is the planning source of truth for what to build next.

Related: [status.md](status.md), [roadmap.md](roadmap.md), [specs/notes-export.md](specs/notes-export.md), [architecture.md](architecture.md), [archived.md](archived.md).

---

## 1. Current state (what already works)

Primary product loop:

```text
Highlight on page → Notes in side panel (local draft) → + Save → ~/.kb/
  → Copy JSON (:::quote fences) → paste into personal site data/*.js
  → Dashboard (web /app/) can browse the same notes document
```

### Shipped and trustworthy enough for daily use

| Area | Notes |
|---|---|
| Notes as source of truth | Editor document owns export; `quotes.json` is highlight IDs only |
| Title field | Single-line normalize; Enter blocked; height capped (no giant-gap autosize) |
| Quote editing | Enter inside quote stays in box; empty Enter exits; Backspace won’t merge commentary into quote |
| Manual quotes | Type `> ` → unlinked blockquote (export yes, page paint no) |
| Copy JSON | DOM → `:::quote` … `:::` matching site `BookshelfPage/data/` shape |
| Delete quote | DOM-first × (no full markdown reparse wipe); linked quotes drop page paint |
| Backend titles | `_normalize_title` on save/update/get/list |
| Launcher | `start.sh` skips Ollama when `OPENAI_API_KEY` is set |
| Smoke | `node scripts/e2e_browser_smoke.mjs` + `tests/test_notes_export.js` |

### Explicitly not done

- Extension day-to-day **correctness holes** (draft paint, write races, reinject)
- **Site scale** features (library-wide export, Saved filters)
- **Context.app integration** for the notes/export loop (Desktop still quote-list)

There is **no extension ↔ Desktop IPC**. Clients share HTTP (`:8765`) and disk (`~/.kb/`). “Integrate into the application” means the macOS UI catching up to the notes document — not inventing a sync bus.

```text
Chrome extension ──┐
Web /app/          ├──► Python :8765 ──► ~/.kb/
Context.app        ─┘
```

---

## 2. Architecture reminder (why pitfalls exist)

| Store | When it matters |
|---|---|
| `chrome.storage.local` `pageDraft:<canonicalUrl>` | Working notes until **+ Save** |
| `~/.kb/library/pages/{id}.json` → `metadata.notes` | What Saved / dashboard / Desktop can see after Save |
| `~/.kb/library/quotes.json` | Highlight IDs + text for on-page paint matching |

Pitfalls cluster where these stores disagree (paint from library only, draft overwritten by panel flush, chat from saved snapshot while tab moved on).

---

## 3. Tier 1 — Correctness pitfalls (fix before features)

These can **lose highlights**, **drop draft quotes**, or **spam SPA navigation**. Highest priority.

### 3.1 On-page paint ignores local drafts after reload

**Symptom:** Highlight with panel closed (or without + Save) → marks appear → hard refresh / revisit → **marks gone**, even though draft + `quotes.json` still have the quote.

**Cause:** Service worker `GET_PAGE_QUOTES` filters with **library** `metadata.notes` only:

- File: [`chrome-extension/background.js`](../chrome-extension/background.js) (`GET_PAGE_QUOTES`)
- `ContextNotes.quotesForHighlights(notes, records)` requires quote bodies to appear in `notes`
- Spec ([notes-export.md](specs/notes-export.md)): drafts are the store until + Save

Panel-open path uses editor notes via `syncHighlightsToPage()` and is fine. Content-script paint after reload goes through the SW path and is not.

**Intended fix:** Load `pageDraft:<url>` via `ContextPageDrafts.loadPageDraft`. Prefer draft notes when nonempty and `draft.updatedAt >= library updated_at` (or library notes empty). Then run `quotesForHighlights`.

**Smoke:** Highlight without Save → reload tab → marks still present. Extend [`scripts/e2e_browser_smoke.mjs`](../scripts/e2e_browser_smoke.mjs).

---

### 3.2 Draft write races (background vs panel)

**Symptom:** Rare lost quote in draft/editor when highlighting while typing in Notes with the panel open.

**Cause:** Two writers:

1. Background `appendQuoteToStoredNotes` on `QUICK_SAVE_QUOTE` ([`background.js`](../chrome-extension/background.js))
2. Panel `schedulePageDraftSave` (150ms debounce) → `persistPageDraft` full form snapshot ([`panel.js`](../chrome-extension/sidepanel/panel.js))

A typing flush that started before `QUOTE_SAVED` updated the editor can write an older `metadata.notes` and **overwrite** the background append.

**Intended fix:**

- Serialize all draft writes through one queue/mutex in [`page-drafts.js`](../chrome-extension/sidepanel/page-drafts.js) (both SW and panel call the same `savePageDraft`)
- On `QUOTE_SAVED`, cancel pending debounce and flush **after** the editor appends the quote
- Prefer merge-on-write for notes (append if missing) rather than blind replace when a concurrent write is detected

---

### 3.3 Reinject nests `history` wrappers

**Symptom:** After “Reload extension”, SPA navigations fire duplicate `PAGE_NAVIGATED` / repaint storms.

**Cause:** [`content/highlights.js`](../chrome-extension/content/highlights.js) `wrapHistory(pushState/replaceState)` on every inject. Teardown removes DOM listeners but **does not unwrap** history. [`content/extract.js`](../chrome-extension/content/extract.js) adds `onMessage` with **no teardown**. `reinjectContentScripts` on `onInstalled` re-executes scripts into open tabs.

**Intended fix:**

- Generation token / idempotent wrap (only wrap if not already wrapped by this extension)
- Explicit unwrap in teardown, or register once via scripting API carefully
- Teardown extract listeners the same way highlights does

---

### 3.4 Delete / unsave library page leaves local draft

**Symptom:** Unsave or delete page → revisit URL → old draft notes reappear as if nothing was removed.

**Cause:** Unsave/delete hits library API but does not call draft clear for that URL ([`panel.js`](../chrome-extension/sidepanel/panel.js) `unsaveCurrentPage`, delete flows).

**Intended fix:** `ContextPageDrafts.clearPageDraft(url)` (new helper) on unsave, delete current page, and clear-library (already has bulk clear path — verify coverage).

---

### 3.5 Chat on saved pages uses stale library snapshot

**Symptom:** After + Save, Ask answers from the **stored** page body, not the current tab (updated article, new selection, fresh paragraphs).

**Cause:** Backend `/ask` prefers `saved_page_id` over live `page` payload ([`core/frontend_backend.py`](../core/frontend_backend.py)). Extension sends both ([`panel.js`](../chrome-extension/sidepanel/panel.js)).

**Intended fix:** When both are present, **persist** chat against `saved_page_id`, but **build context** by overlaying live extraction fields (`paragraphs`, `headings`, `selected_text`, `text`, etc.) onto the saved record.

---

### 3.6 Contenteditable residual risk

**Symptom:** Occasional odd quote DOM after paste / aggressive formatting (less common after 0.1.8).

**Cause:** Notes remain contenteditable + markdown round-trip. `repairBrokenNoteQuotes()` is an empty stub. Full CommonMark is not supported.

**Stance:** Harden edges only if smoke still fails. Do **not** rewrite to ProseMirror unless Tier 1–2 still show breakout after trust fixes. Near-perfect consistency would require a markdown source editor (changes Notes look — separate decision).

---

## 4. Tier 2 — Extension UX / product friction

| Pitfall | Effect | Direction |
|---|---|---|
| Default sub-tab is **Details** | Reading loop starts one click from Notes | Default `pageTab` → `"notes"` |
| **Saved** toggles to unsave with no confirm | Easy wipe of library page | Confirm dialog before DELETE |
| Saved list shows quote counts, not notes | Feels like legacy quote-list product | Card preview = notes excerpt + tags/category |
| No Saved filters | Hard to find pages at scale | Filter by category / tags / medium |
| Author/date auto-fill dead | Content `buildPageContext()` has metadata; SW inject extract does not | Prefer content-script context or merge metadata into SW extract |
| Dual Copy JSON (Details + Notes) | Confusing | One primary control |
| Life/Wiki still in DOM/JS | Noise; archived from nav | Gate or remove dead views |
| PDF quotes save; paint HTML-only | Confusing “missing highlight” | Status: “saved, not painted on this viewer” |
| URL identity | Query/UTM variants split drafts and library | Strip known trackers or document raw-URL policy; use `pageUrlsMatch` everywhere |
| `MAX_DRAFTS = 200` silent GC | Quiet data loss | Warn in Settings or raise cap / LRU with notice |
| Proactive banner “shipped” in roadmap | Not in current side panel HTML | Fix roadmap claim or restore banner |
| `web/notes.js` duplicated from extension | Drift | Documented copy script or single source build |

---

## 5. Tier 3 — Site / bookshelf loop gaps

Per-page Copy JSON works for pasting into `riyer8.github.io` `BookshelfPage/data/*.js`.

| Gap | Why it matters | Direction |
|---|---|---|
| No library-wide export | Cannot dump an array for bulk site update | Saved action or API: `[ ContextBookshelf.format(entry), ... ]` |
| Empty tags emit `['']` | Site may not want a blank tag | Emit `[]` when empty |
| Export URL may include hash/query | Library stores canonical URL | Export canonical URL |
| No write-back to site repo | By design (clipboard) | Keep clipboard; automation is a new product |

Roadmap already lists library-wide export and Saved filters as open ([roadmap.md](roadmap.md) Reading-first).

---

## 6. Tier 4 — Application integration (Context.app) — not started for notes

### What “integrate to the actual application” means

| Layer | Status |
|---|---|
| Shared `~/.kb/` + `:8765` | Done |
| Extension write notes/export | Done |
| Web dashboard render notes + Copy JSON | Done |
| **DesktopApp show/edit/export `metadata.notes`** | **Not done** |

Desktop today ([`DesktopApp/`](../DesktopApp/)):

- Lists saved pages and quote strings via API
- `SavedPageDetail` / library UI are **quote-list** oriented — no `metadata.notes` document
- No Copy JSON / bookshelf export
- Uses `/chat` (memory-wide), not page-aware `/ask`
- Empty state correctly says pages from the extension appear there — but the **notes product loop does not**

### Integration milestone (when chosen)

1. Extend Swift models with `metadata` (notes, tags, tldr, thoughts, dateAdded, …)
2. Render notes markdown in library detail (Swift markdown or WebView)
3. Copy JSON matching [notes-export.md](specs/notes-export.md) (port formatter or embed helpers)
4. Update docs/overview so they don’t claim Desktop has notes until true
5. Optional later: page-aware Ask; design-token alignment ([design.md](design.md) phase 7)

### What it is not

- Not GCal/Gmail/iMessage / Life / Wiki revival ([archived.md](archived.md))
- Not a new extension↔app sync protocol
- Not auto-writing Chrome drafts into `~/.kb/` on every keystroke (collapses the draft model — separate product decision)

**Do not start Desktop notes parity until Tier 1 is green.** Desktop only sees post-Save library data; draft/paint races will look like “the app is broken.”

---

## 7. Explicitly deferred

- Life / Wiki / integrations as product focus
- Obsidian vault sync, Marp, Phase 5 scrapers
- ProseMirror / TipTap Notes rewrite (unless smoke forces it)
- Auto-promote drafts to library without + Save
- Writing directly into the personal site git repo

---

## 8. Recommended sequence

### Sprint A — Extension trust (do next)

1. Draft-aware `GET_PAGE_QUOTES` + Playwright “reload without Save still paints”
2. Draft write mutex + cancel debounce on `QUOTE_SAVED`
3. Reinject / history unwrap + extract teardown
4. Clear draft on unsave/delete
5. `/ask` live overlay when `saved_page_id` + live `page` both present

### Sprint B — Daily UX

6. Default tab → Notes; confirm before unsave
7. Saved cards: notes excerpt (then filters)
8. Wire metadata into page context
9. Trim dual Copy JSON / Life-Wiki dead weight

### Sprint C — Site scale

10. Library-wide bookshelf array export
11. Canonical URL + empty tags `[]` in export
12. Saved filters (category / tags / medium)

### Sprint D — Application integration

13. DesktopApp `metadata.notes` render + Copy JSON
14. Docs honesty + optional `/ask` later

---

## 9. Success criteria (definition of done per sprint)

**Sprint A**

- [ ] Highlight without Save → hard refresh → marks still paint from draft notes
- [ ] Rapid highlight while typing in Notes → no lost quotes in draft or editor
- [ ] Reload extension on an SPA → no duplicate navigation storms
- [ ] Unsave page → draft cleared for that URL
- [ ] Ask after Save still uses fresh tab selection/paragraphs when provided

**Sprint B**

- [ ] Opening a page lands on Notes
- [ ] Unsave requires confirm
- [ ] Saved list shows a notes snippet, not only quote count
- [ ] Author/date (or other DOM metadata) can auto-fill Details when available

**Sprint C**

- [ ] One action copies a JS array of all (or filtered) bookshelf entries
- [ ] Exported URLs match library canonicalization; empty tags are `[]`

**Sprint D**

- [ ] Context.app library detail shows the same notes document as extension Saved / dashboard
- [ ] Desktop can Copy JSON in the site paste shape

---

## 10. Key file map

| Concern | Files |
|---|---|
| Paint / quick-save / drafts in SW | `chrome-extension/background.js`, `sidepanel/page-drafts.js`, `sidepanel/notes.js` |
| Notes editor / save / unsave / ask | `chrome-extension/sidepanel/panel.js`, `index.html`, `panel.css` |
| Content scripts | `chrome-extension/content/highlights.js`, `extract.js` |
| Ask backend | `core/frontend_backend.py`, `core/retrieval/page_chat.py` |
| Export | `chrome-extension/sidepanel/bookshelf-export.js`, `web/bookshelf-export.js` |
| Smoke | `scripts/e2e_browser_smoke.mjs`, `docs/testing.md` |
| Desktop library | `DesktopApp/` `LibraryStore.swift`, `LibraryPanelView.swift` |
| Spec | `docs/specs/notes-export.md` |

---

## 11. How to use this doc

1. Pick the next **Sprint** letter — do not cherry-pick Desktop before trust.
2. Open a focused PR/session per item (or small batch within one sprint).
3. Update [status.md](status.md) when a sprint completes; tick roadmap Reading-first items when Sprint C/D land.
4. Keep Life/Wiki archived unless product direction explicitly changes.
