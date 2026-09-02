"""Privacy eval cases from tests/fixtures/privacy_eval_cases.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "privacy_eval_cases.json"


@pytest.fixture
def isolated_kb(tmp_path, monkeypatch):
    """Each eval case gets its own kb_root so hash maps don't bleed."""
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    from importlib import reload

    import core.config as cfg_mod

    reload(cfg_mod)
    import core.privacy.hasher as hasher_mod
    import core.privacy.pipeline as pipeline_mod

    reload(hasher_mod)
    reload(pipeline_mod)
    yield tmp_path


def _load_cases() -> list[dict]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_privacy_eval_case(case: dict, isolated_kb) -> None:
    from core.privacy.pipeline import process

    inp = case["input"]
    expected = case["expected"]

    result = process(
        text=inp["text"],
        source=inp["source"],
        url=inp.get("url"),
        window_title=inp.get("window_title"),
        app_name=inp.get("app_name"),
        flagged_important=inp.get("flagged_important", False),
    )

    assert result["should_pause"] == expected["should_pause"], case["description"]

    if expected.get("has_person_hash"):
        assert "[PERSON:" in result["text"], case["description"]
        assert "Alice Johnson" not in result["text"]
    elif not expected["should_pause"] and "Johnson" in inp["text"]:
        assert "Johnson" not in result["text"] or "[PERSON:" in result["text"]

    score = result["sensitivity_score"]
    assert expected["sensitivity_score_min"] <= score <= expected["sensitivity_score_max"], (
        f"{case['id']}: score {score} not in "
        f"[{expected['sensitivity_score_min']}, {expected['sensitivity_score_max']}]"
    )

    if not expected["should_pause"] and "@" in inp["text"]:
        assert "@" not in result["text"] or "[EMAIL:" in result["text"], case["description"]
