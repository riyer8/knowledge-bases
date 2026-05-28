# Buckets of Life Spec

## Purpose

Automatically classify all captured events into life categories. This creates a structured
view of how the user actually spends their time, not just screen time — real life signal.

---

## Default Bucket Taxonomy

```
Life
├── Work
│   ├── Deep Work (coding, writing, analysis)
│   ├── Meetings
│   ├── Admin (email, scheduling)
│   └── Learning (courses, docs, tutorials)
├── Relationships
│   ├── Family
│   ├── Friends
│   └── Colleagues
├── Health
│   ├── Exercise
│   ├── Medical
│   ├── Sleep
│   └── Food
├── Finances
│   ├── Transactions
│   ├── Investments
│   └── Planning
├── Home
│   ├── Errands
│   ├── Purchases
│   └── Maintenance
├── Creativity
│   ├── Projects
│   └── Exploration
├── Entertainment
│   ├── Media
│   └── Social
└── Other
```

---

## Classification

Each clean event receives a bucket classification:
- Primary bucket (e.g., "Work/Deep Work")
- Confidence score (0.0–1.0)
- Classification source: "keyword" | "llm" | "user_override"

Classification methods (in order of preference):
1. **Source-based rules**: gcal events → Work or Relationships based on title
2. **Keyword matching**: fast, no LLM needed for obvious cases
3. **LLM classification**: for ambiguous events (use local model via Ollama)
4. **User override**: user can drag events between buckets in UI

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
    "bucket": "Work/Deep Work",
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
