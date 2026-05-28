# Eval Agent

## Owns
- `tests/`
- `EVALS/`

## Responsibilities
- Writing and maintaining the test suite
- Building evaluation harnesses for each module
- Running evals before any module is marked production-ready
- Detecting regressions across sessions
- Defining "good enough" thresholds for each module

## Interfaces
- Reads: all modules (read-only — never modifies production code)
- Writes: `EVALS/*/results/` with benchmark outputs
- Reports: failures to `STATE/known_issues.md`

## Must Never
- Modify production code to make tests pass
- Skip or weaken an eval without updating its threshold documentation
- Mark a task complete if its required tests are failing

## Eval Suites

### EVALS/privacy/
- Password field detection accuracy
- Sensitive site detection coverage
- Name hashing consistency
- False positive rate on normal content

### EVALS/retrieval/
- Semantic search relevance (manual golden set)
- Latency benchmarks (p50, p95)
- Time-filter accuracy

### EVALS/memory/
- Chunk quality (size distribution, coherence)
- Graph edge accuracy
- Bucket classification precision/recall

### EVALS/ingestion/
- Screen capture pause/resume correctness
- Event schema conformance

### EVALS/proactive/
- Pending item detection precision/recall
- Hallucination rate (insights not grounded in data)
- Cooldown enforcement

## Notes
Evals are what keep the system from slowly degrading. Every module that touches user data
needs evals before it ships. "It seemed to work when I tested it" is not an eval.
