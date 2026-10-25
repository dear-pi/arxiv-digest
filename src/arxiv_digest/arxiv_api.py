"""Fetch recent papers from the arXiv API (Atom feed) per category.

Only `cat:` + `submittedDate` queries are used — free-text search endpoints
are far more aggressively rate-limited. One request per category, 3 s apart,
honouring `Retry-After`, as arXiv's API etiquette asks.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

ATOM = "{http://www.w3.org/2005/Atom}"
API_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "arxiv-digest/0.1 (personal study tool)"


@dataclass(frozen=True)
class Paper:
    arxiv_id: str  # 2401.12345v1
    title: str
    authors: list[str]
    categories: list[str]
    abstract: str
    published: datetime
    url: str  # abs page

    @property
    def short_id(self) -> str:
        return self.arxiv_id.split("v")[0]

    @property
    def first_author(self) -> str:
        return self.authors[0] + (" 等" if len(self.authors) > 1 else "")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_query(category: str, start: datetime, end: datetime) -> str:
    return (
        f"cat:{category} AND submittedDate:[{start.strftime('%Y%m%d%H%M')} "
        f"TO {end.strftime('%Y%m%d%H%M')}]"
    )


def parse_atom(xml_text: str) -> list[Paper]:
    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall(f"{ATOM}entry"):
        id_url = (entry.findtext(f"{ATOM}id") or "").strip()
        arxiv_id = id_url.rsplit("/", 1)[-1] if id_url else ""
        if not arxiv_id:
            continue
        published = entry.findtext(f"{ATOM}published") or ""
        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=_clean(entry.findtext(f"{ATOM}title") or ""),
                authors=[
                    _clean(a.findtext(f"{ATOM}name") or "")
                    for a in entry.findall(f"{ATOM}author")
                ],
                categories=[c.get("term", "") for c in entry.findall(f"{ATOM}category")],
                abstract=_clean(entry.findtext(f"{ATOM}summary") or ""),
                published=_parse_dt(published),
                url=f"https://arxiv.org/abs/{arxiv_id}",
            )
        )
    return papers


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def fetch_recent(
    categories: list[str],
    days: int = 3,
    max_per_category: int = 30,
    client: httpx.Client | None = None,
    sleep: float = 3.0,
) -> list[Paper]:
    """Fetch newest papers per category within the last ``days`` days."""
    end = datetime.now(UTC).replace(tzinfo=None)
    start = end - timedelta(days=days)
    own = client is None
    client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT})
    seen: dict[str, Paper] = {}
    try:
        for i, cat in enumerate(categories):
            if i:
                time.sleep(sleep)  # arXiv etiquette: <= 1 request / 3 s
            resp = client.get(
                API_URL,
                params={
                    "search_query": build_query(cat, start, end),
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": max_per_category,
                },
            )
            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", "10"))
                time.sleep(min(wait, 60))
                resp = client.get(
                    API_URL,
                    params={
                        "search_query": build_query(cat, start, end),
                        "sortBy": "submittedDate",
                        "sortOrder": "descending",
                        "max_results": max_per_category,
                    },
                )
            resp.raise_for_status()
            for p in parse_atom(resp.text):
                seen.setdefault(p.short_id, p)
    finally:
        if own:
            client.close()
    return sorted(seen.values(), key=lambda p: p.published, reverse=True)
