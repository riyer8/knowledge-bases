# Integration Agent

## Owns
- `core/integrations/`

## Responsibilities
- Read-only connectors to external services:
  - Google Calendar
  - Gmail
  - iMessage (local DB)
  - Slack
  - Apple Health / fitness apps
- OAuth token management (stored locally, never synced)
- Translating external events into the standard event schema
- Feeding all external events into the ingestion pipeline (same path as screen capture)

## Interfaces
- Emits: raw events to ingestion-agent (same schema as `SPECS/event-schema.md`)
- Reads: external APIs (Google, Slack, etc.)
- Exposes: `/integrations/status`, `/integrations/sync` endpoints

## Must Never
- Write data to external services (read-only, always)
- Store OAuth tokens outside `~/.kb/auth/` (which is gitignored)
- Bypass the ingestion pipeline (all data goes through ingestion → privacy → memory)
- Pull full email bodies by default — pull metadata + subject only unless user opts in

## Required Tests
- Each connector emits valid event schema
- OAuth token refresh works without user intervention
- Read-only enforcement (no write operations exist in connector code)
- Calendar events include correct time context

## Notes
Integrations are Phase 2. Don't build them until Phase 1 (privacy + indexing) is solid.
A broken integration that bypasses the privacy pipeline is a serious problem.
