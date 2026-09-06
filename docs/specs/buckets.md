# Buckets of Life Spec

_Last updated: 2026-09-06_

## Purpose

Automatically classify all captured events into life categories. This creates a structured
view of how the user actually spends their time, not just screen time — real life signal.

**Status today:** backend + Desktop Life panel are implemented. Life is [archived from
extension/dashboard nav](../archived.md). UI requirements below that go beyond the archived
surface (rich filters, create/rename buckets) are target UX, not the current reading-first product.

---

## Default Bucket Taxonomy

Reading-first categories. Saved pages and quotes only appear in Life while
the page is still in the library — unsaved browsing stays out, same as Saved and Graph.

```
Life
├── Work
│   ├── Projects (coding, design, shipping)
│   ├── Meetings
│   └── Admin (email, scheduling)
├── Learning
│   ├── Research
│   ├── Tutorials
│   └── Reference
├── News
├── People
│   ├── Family
│   ├── Friends
│   └── Colleagues
├── Health
│   ├── Fitness
│   ├── Medical
│   └── Food
├── Money
│   ├── Spending
│   ├── Investing
│   └── Planning
├── Home
├── Creative
├── Entertainment
└── Other
```

---

## Classification

Each clean event receives a bucket classification:
- Primary bucket (e.g., "Work/Projects")
- Confidence score (0.0–1.0)
- Classification source: "url_rule" | "keyword" | "llm" | "user_override"

Classification methods (in order of preference):
1. **URL / site rules**: saved article host (github → Work/Projects, nytimes → News)
2. **Source-based rules**: gcal events → Work or People based on title
3. **Keyword matching**: specific phrases only (generic words like "reading" are ignored)
4. **LLM classification**: for ambiguous events (use local model via Ollama)
5. **User override**: user can move events between buckets in the Life tab

Library-backed sources (`saved_page`, `saved_quote`, `browser_remember`) are hidden
from Life unless the related page is still saved. Unsaving or deleting a page
drops it from Life immediately.

---

## UI Requirements

- Tree view of buckets
- Each node shows: event count, time spent (estimated), last activity
- Filterable by:
  - Time range (day, week, month, year, custom)
  - Bucket (select one or more)
  - Source (screen capture, calendar, messages, etc.)
  - Importance flag
- User can rename buckets
- User can create sub-buckets
- User can move events between buckets

---

## Storage

Bucket classifications stored in `~/.kb/buckets/classifications.json`:

```json
{
  "event_id": {
    "bucket": "Work/Projects",
    "confidence": 0.92,
    "source": "llm",
    "user_overridden": false
  }
}
```

---

## Time Tracking

Bucket aggregations computed on-demand from classifications:
- Time spent per bucket per day/week/month
- Based on event timestamps and estimated durations
- Screen capture events: duration from capture metadata
- Calendar events: duration from gcal data
- Manual inputs: 0 duration (point-in-time)
