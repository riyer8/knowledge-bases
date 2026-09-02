# Testing

## Unit tests

Run the full suite:

```bash
pytest tests/ -v
```

Every new function with side effects needs a test in `tests/`.

## Privacy eval cases

Higher-level privacy checks use JSON fixtures in `tests/fixtures/privacy_eval_cases.json`
(20+ cases covering auto-pause, name hashing, email/phone redaction, sensitivity scores).

```bash
pytest tests/test_privacy_eval_cases.py -v
```

These must pass before any change to `core/privacy/`.

### Case format

```json
{
  "id": "tc-001",
  "description": "Banking URL triggers auto-pause",
  "input": {
    "text": "...",
    "source": "screen_capture",
    "url": "https://chase.com/accounts",
    "window_title": null,
    "app_name": null,
    "flagged_important": false
  },
  "expected": {
    "should_pause": true,
    "has_person_hash": false,
    "sensitivity_score_min": 1.0,
    "sensitivity_score_max": 1.0
  }
}
```

## Planned eval suites

| Suite | Status | Threshold |
|---|---|---|
| Privacy | **implemented** | 20+ JSON cases, 0 PII leaks |
| Retrieval | planned | p95 < 2s, recall > 80% |
| Memory | planned | chunk coherence, graph accuracy |
| Ingestion | planned | schema conformance, pause/resume |
| Proactive | planned | hallucination rate, precision |

## Demo seed data

For presentations, seed sample course data:

```bash
python3 demo/seed_demo.py
```

## CI expectation

All tests in `tests/` must pass before marking work complete. Privacy eval cases are part
of that gate.
