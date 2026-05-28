# Evals

Evaluation harnesses for each module. These are not unit tests — they test whether the
system is actually doing the right thing at a higher level.

## Suites

| Suite | Status | Threshold Summary |
|---|---|---|
| `privacy/` | not built yet | PII detection > 99%, 0 leaks |
| `retrieval/` | not built yet | p95 < 2s, recall > 80% |
| `memory/` | not built yet | chunk coherence, graph accuracy |
| `ingestion/` | not built yet | schema conformance, pause/resume |
| `proactive/` | not built yet | hallucination rate, precision |

## Rule

No module ships without its eval suite passing.
If you change a module, run its evals before marking the task complete.

## Running All Evals

```bash
python -m pytest EVALS/ -v
```
