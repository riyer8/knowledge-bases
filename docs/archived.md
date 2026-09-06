# Archived surfaces

_Last updated: 2026-09-06_

Life and Wiki are **hidden from nav**, not deleted. The reading loop (highlight → notes → bookshelf JSON) is the product. Revive by restoring a nav button; the views and backend already exist.

## What is archived

| Surface | UI (hidden) | Backend |
|---|---|---|
| **Life** | Extension `#view-life`, dashboard `#view-life` | `/buckets/*`, `/dashboard/time`, `core/memory/buckets_service.py` |
| **Wiki** | Extension `#view-wiki`, dashboard `#view-wiki` | `/wiki/*`, `core/wiki_service.py`, `~/.kb/wiki/` |
| **Integrations** | No primary nav | GCal, Gmail, iMessage under `core/integrations/` |
| **Desktop pet / proactive** | macOS app only | `core/proactive/` |

## How to revive

1. Uncomment the nav buttons in [`chrome-extension/sidepanel/index.html`](../chrome-extension/sidepanel/index.html) and [`web/index.html`](../web/index.html) (`data-view="life"` / `data-view="wiki"`).
2. Remove the early return in `switchView` that ignores `life` and `wiki`.
3. Keep storage write rules in [storage.md](storage.md).

Do not start a second repo. Archived code stays here until you explicitly delete it.
