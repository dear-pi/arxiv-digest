"""Shared test doubles: offline papers and a scripted chat client."""

from __future__ import annotations

from datetime import datetime

from arxiv_digest.arxiv_api import Paper


def PaperStub(i: str, title: str = "paper", relevance_hint: str = "") -> Paper:  # noqa: N802
    return Paper(
        arxiv_id=f"{i}v1",
        title=f"{title} {i} {relevance_hint}".strip(),
        authors=["Alice Chen", "Bob Li"],
        categories=["cs.AI"],
        abstract="an abstract about agents and tools",
        published=datetime(2026, 10, 20, 12, 0),
        url=f"https://arxiv.org/abs/{i}",
    )


class ScriptedClient:
    """Returns queued responses in order; records every call."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def chat(self, system: str, user: str) -> str:
        self.calls += 1
        return self.responses.pop(0) if self.responses else ""
