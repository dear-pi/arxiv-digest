"""CLI end-to-end (offline): fetch is monkeypatched, LLM disabled."""

from __future__ import annotations

import argparse

from testsutil import PaperStub

from arxiv_digest import cli


def run_cli(tmp_path, monkeypatch, extra: list[str]) -> object:
    papers = [PaperStub("aaa.1"), PaperStub("bbb.2"), PaperStub("aaa.1")]
    unique = [papers[0], papers[1]]
    monkeypatch.setattr(cli, "fetch_recent", lambda *a, **kw: unique)
    args = argparse.Namespace(
        days=3, categories="cs.AI", max_per_category=30, max=40,
        no_llm=True, include_seen=False,
        out=str(tmp_path / "digests"), state=str(tmp_path / "state.json"),
    )
    for flag in extra:
        setattr(args, flag.replace("--", "").replace("-", "_"), True)
    return cli.run(args), args


def test_run_no_llm_writes_digest_and_state(tmp_path, monkeypatch):
    rc, _ = run_cli(tmp_path, monkeypatch, [])
    assert rc == 0
    digest = list((tmp_path / "digests").glob("*.md"))
    assert len(digest) == 1
    content = digest[0].read_text(encoding="utf-8")
    assert "paper aaa.1" in content and "未启用" in content
    state = (tmp_path / "state.json").read_text(encoding="utf-8")
    assert "aaa.1" in state and "bbb.2" in state


def test_second_run_skips_seen(tmp_path, monkeypatch):
    run_cli(tmp_path, monkeypatch, [])
    rc, _ = run_cli(tmp_path, monkeypatch, [])
    assert rc == 0
    # 第二次全部已见过 → 不再写新日报
    assert len(list((tmp_path / "digests").glob("*.md"))) == 1
