"""Render the Markdown daily digest."""

from __future__ import annotations

from datetime import datetime

from .arxiv_api import Paper
from .summarize import Summary


def _stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n)


def build_markdown(
    papers: list[Paper],
    summaries: dict[str, Summary],
    *,
    days: int,
    categories: list[str],
    llm_label: str,
    skipped_seen: int = 0,
    summarize_failures: int = 0,
) -> str:
    ranked = sorted(
        papers,
        key=lambda p: (summaries.get(p.short_id).relevance if p.short_id in summaries else 0),
        reverse=True,
    )
    hot = [p for p in ranked if p.short_id in summaries and summaries[p.short_id].relevance >= 4]

    lines = [
        f"# arXiv 论文日报 · {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"> 窗口：最近 {days} 天 · 类目：{' / '.join(categories)} · "
        f"收录 {len(papers)} 篇（去重跳过 {skipped_seen} 篇旧文） · 总结模型：{llm_label}",
        "",
    ]

    if hot:
        lines += ["## 今日值得关注（相关度 ≥ 4）", ""]
        for p in hot:
            s = summaries[p.short_id]
            lines += [
                f"### {_stars(s.relevance)} [{p.title}]({p.url})",
                "",
                f"- {p.first_author} · {', '.join(p.categories)} · `{p.short_id}`",
                f"- **一句话**：{s.one_line}",
                f"- **为什么关注**：{s.why_care}",
                "",
            ]

    lines += ["## 全部论文", ""]
    for p in ranked:
        s = summaries.get(p.short_id)
        tag = f" `{s.relevance}★` " if s else " "
        lines.append(f"- [{p.title}]({p.url}){tag}· {p.first_author} · `{p.short_id}`")
        if s:
            lines.append(f"  - {s.one_line}")
    lines += [""]

    if summarize_failures:
        lines.append(f"> 注：{summarize_failures} 篇的 LLM 总结失败，仅列出条目。")
        lines.append("")
    return "\n".join(lines)


def digest_filename(out_dir: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    base = now.strftime("%Y-%m-%d")
    path = f"{out_dir}/{base}.md"
    i = 2
    from pathlib import Path

    while Path(path).exists():
        path = f"{out_dir}/{base}-{i}.md"
        i += 1
    return path
