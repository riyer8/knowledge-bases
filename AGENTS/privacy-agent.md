# Privacy Agent

## Owns
- `core/privacy/`

## Responsibilities
- Credential and password field detection
- Banking and sensitive site URL detection → emit pause signal to ingestion
- PII detection (names, emails, phone numbers, addresses)
- Name hashing: SHA-256 + per-install salt, stored in `~/.kb/hashes/map.json`
- Sensitivity scoring (0.0–1.0) on each event
- Writing sanitized events to `~/.kb/events/clean/`
- Maintaining the sensitive sites list (`core/privacy/sensitive_sites.py`)

## Interfaces
- Receives: raw events from `~/.kb/events/raw/`
- Emits: clean events to `~/.kb/events/clean/`
- Emits: pause/resume signals to ingestion-agent
- Exposes: no HTTP endpoints (internal pipeline only)

## Must Never
- Modify the retrieval layer
- Store unhashed identities anywhere in the system
- Bypass hash verification tests
- Expose the hash→name map over any API endpoint
- Remove or weaken detection logic without updating `EVALS/privacy/`

## Required Tests
- Password field detection (true positive rate > 99%)
- Banking site detection from sensitive_sites.py
- Name extraction and hashing produces consistent output
- Hash→display rendering round-trips correctly
- Sensitivity scoring returns float in [0.0, 1.0]
- Clean events contain no raw PII

## Notes
This is the most critical module in the system. A bug here is worse than a missing feature
anywhere else. Never ship changes to this module without running the full eval suite.
The privacy pipeline is a mandatory gate — no data reaches memory without passing through it.
