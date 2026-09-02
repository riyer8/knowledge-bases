# Context — Design System

_Last updated: 2026-09-02_

This document defines the visual language, interaction patterns, and implementation
plan for **Context** across the Chrome extension, local dashboard (`/app/`), and macOS app.

Product thesis (from [vision.md](vision.md)): *An AI that remembers what you've learned.*
The UI should feel like a **quiet study** — focused, trustworthy, local-first — not a chatbot
dashboard.

---

## Design principles

| Principle | Meaning |
|---|---|
| **Reading first** | Typography and whitespace beat decoration. The page you're on is the hero. |
| **Memory, not noise** | Saved pages, quotes, and connections surface gently; nothing shouts for attention. |
| **Local & private** | Dark-by-default evokes “on your machine.” No analytics chrome, no engagement bait. |
| **One backend, many faces** | Extension (narrow), dashboard (wide), desktop (native) share tokens and behavior. |
| **Progressive depth** | Page → Saved → Graph → Wiki → Life: shallow first, detail on demand. |

---

## Brand

- **Name:** Context
- **Mark:** ◇ (diamond) — connection, graph node, “spark” of insight
- **Voice:** Short labels. No “Clear memory” — say **Delete page**. No jargon in primary UI.
- **Tone:** Calm, precise, slightly literary (fits reading & quotes).

---

## Color system

### Accent — **Periwinkle** `#7c9cff`

Chose over pink/purple: readable on dark, distinct from danger red, feels “thoughtful” not “startup.”

| Token | Dark | Light | Use |
|---|---|---|---|
| `--accent` | `#7c9cff` | `#4f6ef7` | Primary actions, links, active nav |
| `--accent-soft` | `rgba(124,156,255,0.12)` | `rgba(79,110,247,0.10)` | Hover, selected rows |
| `--accent-strong` | `#9eb4ff` | `#3b5bdb` | Hover on primary buttons |

### Surfaces

| Token | Dark | Light |
|---|---|---|
| `--bg` | `#0b0d12` | `#f4f6fb` |
| `--panel` | `#141820` | `#ffffff` |
| `--panel-2` | `#1c2230` | `#eef1f8` |
| `--border` | `#2a3140` | `#e2e8f0` |

### Text

| Token | Dark | Light |
|---|---|---|
| `--text` | `#f3f4f6` | `#111827` |
| `--muted` | `#9ca3af` | `#6b7280` |

### Semantic

| Token | Value | Use |
|---|---|---|
| `--danger` | `#f87171` | Delete, destructive confirm |
| `--success` | `#34d399` | Saved badge, quote saved |
| `--warning` | `#fbbf24` | Setup hints |

---

## Theme modes

Three modes, synced per client via `localStorage` key `context-theme`:

1. **System** (default) — follows `prefers-color-scheme`
2. **Dark** — default brand experience
3. **Light** — daytime / bright environments

Implementation: `data-theme="dark|light"` on `<html>`, tokens in `web/tokens.css` (mirrored in extension).

Toggle locations:
- Extension → Settings → Appearance
- Dashboard → Settings → Appearance

---

## Typography

| Role | Size | Weight | Use |
|---|---|---|---|
| Display | 22–24px | 600 | Dashboard page titles |
| Title | 17–18px | 600 | Page title field, saved detail |
| Body | 13–15px | 400 | Chat, summaries, markdown |
| Caption | 11–12px | 400–500 | URLs, timestamps, view intros |
| Label | 10–11px | 600 | Uppercase section labels (Quotes, Summary) |

**Font stack:** `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`  
**Monospace:** `ui-monospace, SFMono-Regular, Menlo, monospace` (code blocks)

Line height: **1.55** body, **1.35** headings.

---

## Spacing & radius

| Token | Value |
|---|---|
| `--space-xs` | 4px |
| `--space-sm` | 8px |
| `--space-md` | 12px |
| `--space-lg` | 16px |
| `--space-xl` | 24px |
| `--radius-sm` | 8px |
| `--radius-md` | 12px |
| `--radius-lg` | 16px |

Extension side panel content padding: **14px** horizontal.

---

## Components

### Buttons

| Variant | Use |
|---|---|
| **Primary** | Save page, Send, Compile — accent fill |
| **Ghost** | Secondary actions, Open dashboard |
| **Text** | Refresh, navigation links |
| **Danger** | Delete page — outline or soft fill |

Min tap height: **36px** in extension, **40px** in dashboard.

### Navigation

- **Extension:** horizontal tabs (Page | Saved | Life | Graph | Wiki) + gear for Settings
- **Dashboard:** left sidebar with active state (`accent-soft` background)
- **Page sub-nav:** Quotes | Chat segmented control

### Cards

- Saved page cards: title, site, summary preview, delete on hover/right
- Quote cards: left accent border, italic blockquote
- Wiki article cards: title + excerpt

### Chat

- User: neutral panel background
- Assistant: `accent-soft` background + **markdown** rendering
- Streaming: plain text during stream, markdown on complete

### Empty states

Centered, muted, one line of guidance + optional action.  
Example: *“Highlight text on the page to save a quote here.”*

### Status bar (extension footer)

Single line: connection state, last action. Errors in `--danger`.

---

## Feature-specific UX

### Page (extension)

1. Header: title (editable), URL, collapsible Details, Save / + Wiki / Explore
2. Sub-tabs: Quotes (default) | Chat
3. Selection bar appears when text highlighted on page
4. Quote compose: inline card with preview + note

### Saved

- List → detail drill-down
- Detail: summary (markdown), quotes, chat history, Delete page, Add to wiki
- Delete from list **or** detail

### Graph

- Page nodes only, linked by shared topics
- Click node → open in Saved / Library
- Empty: “Save pages to see connections”

### Wiki

- Extension: compact list + ask; link to full dashboard
- Dashboard: sidebar (index / articles / raw) + markdown reader + compile + health + ask

### Life

- Bucket chips (7-day breakdown)
- Event cards with bucket dropdown + Save override

### Settings

- Backend status, AI provider, Appearance (theme), Dashboard link, Data controls

---

## Motion

- Transitions: **150ms** color/border only — no layout animation
- No auto-playing carousels or banner slides
- Confirm dialogs: fade overlay, no bounce

---

## Accessibility

- `color-scheme` matches active theme
- `:focus-visible` ring using `--accent`
- Contrast: body text ≥ 4.5:1 on panels (both themes)
- Icon buttons require `aria-label`
- Confirm dialogs: `role="dialog"` `aria-modal="true"`

---

## Surfaces map

| Surface | Width | Primary actions |
|---|---|---|
| Chrome side panel | ~360px | Save quote, chat, save page |
| Dashboard `/app/` | full browser | Browse library, graph, wiki, life |
| macOS app | native windows | Same API, SwiftUI (follow tokens in future pass) |

---

## Implementation phases

| Phase | Deliverable | Status |
|---|---|---|
| **1** | `docs/design.md` (this file) | Done |
| **2** | `tokens.css` + `theme.js` (dark/light/system) | Done |
| **3** | Extension: import tokens, theme toggle, polish | Done |
| **4** | Dashboard: import tokens, theme toggle, polish | Done |
| **5** | Shared markdown styles per tokens | Done |
| **6** | Tests: markdown unit tests, e2e page delete + flows | Done |
| **7** | macOS SwiftUI color alignment | Future |

---

## File locations

```text
web/tokens.css          # Canonical design tokens
web/theme.js            # Theme init + toggle API
web/markdown.js         # Markdown renderer
chrome-extension/sidepanel/tokens.css   # Mirror of web/tokens.css
chrome-extension/sidepanel/theme.js     # Mirror of web/theme.js
chrome-extension/sidepanel/panel.css      # Extension components
web/app.css                               # Dashboard layout + components
```

When changing tokens, update **both** `web/tokens.css` and `chrome-extension/sidepanel/tokens.css`
(or consolidate via copy script in a future pass).

---

## References

- [vision.md](vision.md) — product modes (Understand, Connect, Learn, Explore)
- [overview.md](overview.md) — feature matrix
- [api.md](api.md) — backend contracts
- [storage.md](storage.md) — data model
