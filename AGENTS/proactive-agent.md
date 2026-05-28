# Proactive Agent

## Owns
- `core/proactive/`

## Responsibilities
- Pending item detection (unanswered messages, emails not replied to)
- Life balance pattern detection (e.g., no health signal in 2 weeks)
- Relationship drift detection (no interaction with hashed person X in N days)
- Generating human-readable insight summaries (via `core/llm_service.py`)
- Scheduling pop-up cadence (configurable, default: end-of-day check)
- Logging all proactive insights so user can review history

## Interfaces
- Reads: clean events from `~/.kb/events/clean/`
- Reads: graph and index via `core/retrieval/`
- Exposes: `/proactive` GET endpoint — returns pending insights for frontend
- Sends: pop-up trigger to `DesktopApp/` when insight is ready

## Must Never
- Take any action on behalf of the user (never auto-send messages, never auto-create events)
- Surface insights based on raw events (must go through privacy pipeline first)
- Spam the user — enforce minimum cooldown between pop-ups (configurable)
- Hallucinate patterns — every insight must be grounded in actual indexed events

## Required Tests
- Pending item detection correctly identifies unanswered threads
- Cooldown prevents duplicate pop-ups within window
- Insight generation references real events (not hallucinated)
- Pattern detection handles empty data gracefully

## Notes
The proactive bot is the most user-facing intelligence feature. Its value depends entirely
on the quality of the data pipeline beneath it. Build it last in each phase — it amplifies
whatever is already working, but it can't compensate for bad data.
