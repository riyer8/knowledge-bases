#!/usr/bin/env python3
"""Seeds the KB with Symsys161 demo data. Run before presenting."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.ingestion.pipeline import ingest_text

_EVENTS = [
    (
        "Symsys 161: Technology and Human Augmentation — Speaker Series. "
        "Stanford Symbolic Systems program. Weekly guest speakers from AI, HCI, and cognitive science "
        "discussing how technology extends human capability. Grading: attendance 30%, "
        "reaction papers 40%, final presentation 30%. "
        "Canvas deadline: final 10-minute demo presentation on a personal project "
        "that augments human memory or cognition.",
    ),
    (
        "Symsys 161 Canvas rubric for final presentation: "
        "Is the harness clear — does the audience understand what they are watching at every step? "
        "Is the problem statement compelling before the solution is shown? "
        "Does the demo close the full loop from capture to retrieval? "
        "Is there a connection to course themes: augmentation, passive capture, memory, attention? "
        "10-minute demo plus 5-minute Q&A. Working prototype required.",
    ),
    (
        "Speaker series class guest talk notes — passive capture systems: "
        "The best memory tool is one you never have to think about using. "
        "Active recall requires effort and therefore fails at scale. "
        "Passive capture — logging what you already do — is the breakthrough pattern. "
        "Examples: Rewind AI, Notion AI, Copilot for meetings. "
        "Key differentiator: local-first privacy vs cloud dependency.",
    ),
    (
        "Symsys 161 presentation prep notes for Sift demo: "
        "Show the full loop live: press Cmd+Shift+S to capture screen, "
        "open chat with Cmd+Shift+C, ask 'what did I just read?' "
        "Highlight the butterfly indicator that flashes red when capturing. "
        "Show the knowledge graph — pink events, blue people, green topics. "
        "Potential risks: LLM latency if Ollama is cold, empty graph if no data. "
        "Fix: run seed_demo.py before the talk so answers are fast and relevant.",
    ),
    (
        "Symsys 161 course themes and how Sift connects: "
        "Memory augmentation — Sift acts as passive external memory that captures without interruption. "
        "Privacy-first design — all processing is local, no data leaves the machine. "
        "Knowledge graph — shows how events, people, and topics relate over time. "
        "Proactive nudges — the butterfly surfaces things you forgot to follow up on. "
        "Frame it as: not a productivity app, a cognitive extension.",
    ),
]


def main() -> None:
    print("Seeding Symsys161 demo events into ~/.kb/...")
    for i, (text,) in enumerate(_EVENTS):
        result = ingest_text(text=text, source="manual_text")
        print(f"  [{i + 1}/{len(_EVENTS)}] {result.get('id', '?')}")
    print("Done — demo data ready. Start the app and ask about Symsys161.")


if __name__ == "__main__":
    main()
