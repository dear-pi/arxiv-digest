"""CLI entry point.

    arxiv-digest run [--days 3] [--categories cs.AI,cs.CL,cs.LG] [--max 40]
                     [--no-llm] [--include-seen] [--out digests] [--state digests/state.json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .arxiv_api import fetch_recent
from .digest import build_markdown, digest_filename
from .state import SeenState
from .summarize import OpenAICompatibleClient, summarize_batch

DEFAULT_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]


def run(args: argparse.Namespace) -> int:
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    print(f"fetching {categories} (last {args.days} days) ...")
    papers = fetch_recent(categories, days=args.days, max_per_category=args.max_per_category)
    print(f"fetched {len(papers)} unique papers")

    state = SeenState.load(args.state)
    skipped = 0
    if not args.include_seen:
        skipped = len(papers) - len(state.filter_new(papers))
        papers = state.filter_new(papers)
        print(f"{len(papers)} new ({skipped} seen before, skipped)")

    if not papers:
        print("nothing new today — no digest written")
        return 0

    client = OpenAICompatibleClient()
    summaries: dict = {}
    failures = 0
    if args.no_llm or not client.available:
        llm_label = "未启用（无 key / --no-llm）"
        print("no-LLM mode: listing papers without summaries")
    else:
        llm_label = client.model
        capped = papers[: args.max]
        print(f"summarizing up to {len(capped)} papers with {client.model} ...")
        summaries = summarize_batch(client, capped, max_papers=args.max)
        failures = len(capped) - len(summaries)
        note = f" ({failures} failed)" if failures else ""
        print(f"summarized {len(summaries)}/{len(capped)}{note}")

    md = build_markdown(
        papers,
        summaries,
        days=args.days,
        categories=categories,
        llm_label=llm_label,
        skipped_seen=skipped,
        summarize_failures=failures,
    )
    out_path = digest_filename(args.out)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(md, encoding="utf-8")
    state.mark_seen(papers)
    state.save()
    print(f"digest written: {out_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="arxiv-digest", description="arXiv 论文日报管道")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="抓取→去重→总结→生成日报")
    r.add_argument("--days", type=int, default=3)
    r.add_argument("--categories", type=str, default=",".join(DEFAULT_CATEGORIES))
    r.add_argument("--max-per-category", type=int, default=30)
    r.add_argument("--max", type=int, default=40, help="每次最多给多少篇做 LLM 总结")
    r.add_argument("--no-llm", action="store_true", help="不调 LLM，只列论文")
    r.add_argument("--include-seen", action="store_true", help="包含已见过的论文")
    r.add_argument("--out", type=str, default="digests")
    r.add_argument("--state", type=str, default="digests/state.json")
    r.set_defaults(func=run)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
