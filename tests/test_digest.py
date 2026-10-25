from datetime import datetime
from pathlib import Path

from testsutil import PaperStub

from arxiv_digest.digest import build_markdown, digest_filename
from arxiv_digest.summarize import Summary


def test_digest_layout_with_and_without_summaries():
    papers = [PaperStub("1"), PaperStub("2")]
    summaries = {
        "1": Summary("工具调用框架", "贴近 Agent 开发", 5),
        "2": Summary("普通研究", "一般相关", 2),
    }
    md = build_markdown(
        papers, summaries, days=3, categories=["cs.AI", "cs.CL"], llm_label="deepseek-chat",
        skipped_seen=7, summarize_failures=1,
    )
    assert "# arXiv 论文日报" in md
    assert "今日值得关注" in md
    assert "★★★★★" in md  # 高分条目的五星渲染
    assert "`2★`" in md  # 低分条目在全部列表中的短标记
    assert "工具调用框架" in md
    assert "https://arxiv.org/abs/1" in md
    assert "去重跳过 7 篇" in md
    assert "1 篇的 LLM 总结失败" in md
    # 高分论文应排在低分前面
    assert md.index("paper 1") < md.index("paper 2")


def test_digest_no_llm_mode():
    papers = [PaperStub("1")]
    md = build_markdown(papers, {}, days=1, categories=["cs.AI"], llm_label="未启用")
    assert "全部论文" in md
    assert "今日值得关注" not in md
    assert "未启用" in md


def test_digest_filename_avoids_collision(tmp_path):
    first = digest_filename(str(tmp_path), now=datetime(2026, 10, 25, 9, 0))
    assert Path(first).name == "2026-10-25.md"
    Path(first).write_text("x", encoding="utf-8")
    second = digest_filename(str(tmp_path), now=datetime(2026, 10, 25, 10, 0))
    assert Path(second).name == "2026-10-25-2.md"
