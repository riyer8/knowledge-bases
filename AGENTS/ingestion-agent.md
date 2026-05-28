# Ingestion Agent

## Owns
- `core/ingestion/`
- `inputs/`

## Responsibilities
- Screen capture lifecycle (start, stop, pause, resume)
- Importance flagging during capture
- Manual input handling (text, files, URLs)
- Screenshot processing (extract text → delete image)
- Raw event emission to `~/.kb/events/raw/`
- Triggering privacy pipeline after each event is written

## Interfaces
- Emits: raw event objects (schema in `SPECS/event-schema.md`)
- Receives: pause/resume signals from privacy-agent
- Exposes: `/ingest`, `/screenshot` endpoints

## Must Never
- Store raw screenshots after text extraction
- Write clean events directly (privacy-agent owns that step)
- Bypass or skip the privacy pipeline
- Log any captured text to stdout

## Required Tests
- Screen capture start/stop/pause cycle
- Importance flagging persists correctly
- Manual input of text, file, URL each produce valid events
- Raw event format matches schema in `SPECS/event-schema.md`
- Screenshot text extraction + image deletion

## Notes
The ingestion agent is the first touch point for all data. Its only job is to capture faithfully
and hand off to privacy. It should have no opinions about what data means.
