# TASK-002: Build core/privacy/ module

- **Status**: complete
- **Owner**: privacy-agent
- **Phase**: 1
- **Created**: 2026-05-19
- **Completed**: 2026-05-27

## Goal
Build the privacy pipeline — the mandatory gate that all data must pass through before
being stored. This is the most critical module in the system. A bug here is worse than
any missing feature.

## Scope
- `core/privacy/__init__.py` (create)
- `core/privacy/detector.py` — PII + credential detection
- `core/privacy/hasher.py` — name hashing + hash map management
- `core/privacy/scorer.py` — sensitivity scoring
- `core/privacy/pipeline.py` — orchestrates the above
- `core/privacy/sensitive_sites.py` — list of banking/sensitive URLs
- `tests/test_privacy.py` (create)
- `EVALS/privacy/` setup

## Requirements
- [ ] Password field detection (heuristic: input[type=password], common CSS selectors)
- [ ] Banking/sensitive URL detection from sensitive_sites.py list
- [ ] Name detection using spaCy or regex patterns
- [ ] SHA-256 + per-install salt hashing (salt stored in `~/.kb/hashes/salt`)
- [ ] Hash → display name map stored in `~/.kb/hashes/map.json`
- [ ] Sensitivity score (0.0–1.0) returned with every processed event
- [ ] Pipeline takes raw event, returns clean event + score
- [ ] Auto-pause signal: boolean flag in pipeline output

## Dependencies
- TASK-001 (needs config for storage paths)
- Read `SPECS/privacy-pipeline.md` before implementing

## Success Criteria
- [ ] Password detection true positive rate > 99% on test cases
- [ ] No raw names in clean event output
- [ ] Hash→display round-trip works correctly
- [ ] Sensitivity score is float in [0.0, 1.0]
- [ ] All tests in `tests/test_privacy.py` pass
- [ ] `EVALS/privacy/` has at least 20 test cases

## Notes
Use spaCy's `en_core_web_sm` for NER (name detection). It's fast enough for real-time
use and doesn't require an API call. Install it in requirements.txt.
