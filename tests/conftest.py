"""Shared pytest fixtures."""
from __future__ import annotations

import re
from dataclasses import dataclass

import pytest


@dataclass
class _FakeEnt:
    text: str
    label_: str
    start_char: int
    end_char: int


class _FakeDoc:
    def __init__(self, text: str) -> None:
        self.ents: list[_FakeEnt] = []
        seen: set[tuple[int, int]] = set()

        for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
            span = (match.start(), match.end())
            if span not in seen:
                seen.add(span)
                self.ents.append(_FakeEnt(match.group(1), "PERSON", span[0], span[1]))

        for match in re.finditer(r"\b(?:with|called|from|by)\s+([A-Z][a-z]+)\b", text):
            name = match.group(1)
            start = match.start(1)
            end = match.end(1)
            span = (start, end)
            if span not in seen:
                seen.add(span)
                self.ents.append(_FakeEnt(name, "PERSON", start, end))


class _FakeNlp:
    def __call__(self, text: str) -> _FakeDoc:
        return _FakeDoc(text)


@pytest.fixture(autouse=True)
def mock_spacy_nlp(monkeypatch):
    """Provide deterministic NER in tests without requiring spaCy installed."""
    import core.privacy.detector as detector_mod

    monkeypatch.setattr(detector_mod, "_get_nlp", lambda: _FakeNlp())
    monkeypatch.setattr(detector_mod, "_nlp", None, raising=False)
