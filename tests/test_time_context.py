"""Tests for core/retrieval/time_context.py."""
from __future__ import annotations


def test_calendar_context_block_empty_when_no_events(monkeypatch):
    monkeypatch.setattr(
        "core.retrieval.time_context.upcoming_events",
        lambda minutes_ahead=240: [],
    )
    from core.retrieval.time_context import calendar_context_block

    assert calendar_context_block() == ""


def test_calendar_context_block_formats_events(monkeypatch):
    monkeypatch.setattr(
        "core.retrieval.time_context.upcoming_events",
        lambda minutes_ahead=240: [
            {"summary": "Team sync", "start": {"dateTime": "2026-05-27T15:00:00Z"}},
        ],
    )
    from core.retrieval.time_context import calendar_context_block

    block = calendar_context_block()
    assert "Team sync" in block
    assert "Upcoming calendar" in block
