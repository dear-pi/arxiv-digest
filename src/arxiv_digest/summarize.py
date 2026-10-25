"""LLM summarization: one Chinese one-liner + why-it-matters + 1–5 relevance.

Key-gated (OpenAI-compatible endpoint, DeepSeek by default). Without a key the
pipeline still runs in no-LLM mode — digests then list papers without
summaries. Output JSON is validated; one retry with a stricter nudge, then a
per-paper fallback so one bad response never kills the run.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Protocol

from .arxiv_api import Paper

SYSTEM_PROMPT = (
    "你是 arXiv 论文编辑。给定一篇论文的标题、作者和摘要，输出 JSON："
    '{"one_line": "<中文一句话概括它做了什么，25字以内，不要空话>", '
    '"why_care": "<中文说明为什么值得关注，30字以内，说具体点>", '
    '"relevance": <1-5整数，5=与『LLM应用/Agent开发』高度相关>}。'
    "只输出这个 JSON，不要任何其他文字。"
)


@dataclass(frozen=True)
class Summary:
    one_line: str
    why_care: str
    relevance: int  # 1-5


class ChatClient(Protocol):
    def chat(self, system: str, user: str) -> str: ...


class OpenAICompatibleClient:
    """Thin wrapper; configure via AD_LLM_API_KEY / AD_LLM_BASE_URL / AD_LLM_MODEL."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("AD_LLM_API_KEY", "")
        self.base_url = os.environ.get("AD_LLM_BASE_URL", "https://api.deepseek.com")
        self.model = os.environ.get("AD_LLM_MODEL", "deepseek-chat")
        self._inner = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _load(self):
        if self._inner is None:
            if not self.api_key:
                raise RuntimeError("no API key: set AD_LLM_API_KEY")
            from openai import OpenAI

            self._inner = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._inner

    def chat(self, system: str, user: str) -> str:
        resp = self._load().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
        )
        return resp.choices[0].message.content or ""


def extract_json(text: str) -> dict:
    """Best-effort JSON extraction: strip fences, take the first {...} block."""
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"no JSON object in response: {text[:60]!r}")
    return json.loads(m.group(0))


def parse_summary(raw: str) -> Summary:
    data = extract_json(raw)
    relevance = int(data["relevance"])
    if not 1 <= relevance <= 5:
        raise ValueError(f"relevance out of range: {relevance}")
    one_line = str(data["one_line"]).strip()
    why_care = str(data["why_care"]).strip()
    if not one_line or not why_care:
        raise ValueError("empty summary field")
    return Summary(one_line=one_line, why_care=why_care, relevance=relevance)


def build_user_prompt(paper: Paper) -> str:
    abstract = paper.abstract[:1500]
    return (
        f"标题: {paper.title}\n作者: {', '.join(paper.authors[:5])}\n"
        f"类目: {', '.join(paper.categories)}\n摘要: {abstract}"
    )


def summarize_paper(client: ChatClient, paper: Paper) -> Summary | None:
    """Summarize one paper; one retry, then give up for this paper only."""
    user = build_user_prompt(paper)
    for prompt in (user, user + "\n\n注意：只输出 JSON 对象本身。"):
        try:
            return parse_summary(client.chat(SYSTEM_PROMPT, prompt))
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
    return None


def summarize_batch(
    client: ChatClient, papers: list[Paper], max_papers: int = 40
) -> dict[str, Summary]:
    out: dict[str, Summary] = {}
    for p in papers[:max_papers]:
        s = summarize_paper(client, p)
        if s is not None:
            out[p.short_id] = s
    return out
