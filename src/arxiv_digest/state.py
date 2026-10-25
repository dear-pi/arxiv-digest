"""Seen-paper state: a small JSON file so consecutive runs only report new papers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .arxiv_api import Paper


@dataclass
class SeenState:
    path: Path
    seen: dict[str, str]  # short_id -> iso date first seen

    @classmethod
    def load(cls, path: str | Path) -> SeenState:
        p = Path(path)
        if p.exists():
            return cls(p, json.loads(p.read_text(encoding="utf-8")))
        return cls(p, {})

    def filter_new(self, papers: list[Paper]) -> list[Paper]:
        return [p for p in papers if p.short_id not in self.seen]

    def mark_seen(self, papers: list[Paper]) -> None:
        now = datetime.now().strftime("%Y-%m-%d")
        for p in papers:
            self.seen[p.short_id] = now

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.seen, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8",
        )
