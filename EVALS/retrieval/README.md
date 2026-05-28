# Retrieval Evals

Tests that the retrieval system returns relevant, accurate results.

## Test Suites

### 1. Semantic Relevance (Golden Set)

A manually curated set of (query, expected_result) pairs.
Run queries against the index. Check that expected results appear in top-5.

Threshold: top-5 recall > 80% on golden set.

File: `golden_set.json`

### 2. Latency Benchmark

Run 50 representative queries. Measure end-to-end latency.

Thresholds:
- p50 < 500ms
- p95 < 2000ms

### 3. Time Filter Accuracy

Queries with explicit time constraints ("last week", "in March").
Expected: only events within that window returned.

Threshold: 100% time filter correctness.

### 4. No PII in Responses

Run 20 queries that could trigger PII-heavy results.
Check that responses contain hashes, not raw names.

Threshold: 0 raw PII in any response.

## Running Evals

```bash
python -m pytest EVALS/retrieval/ -v
```
