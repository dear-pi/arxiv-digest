import pytest
from testsutil import PaperStub, ScriptedClient

from arxiv_digest.summarize import (
    Summary,
    extract_json,
    parse_summary,
    summarize_batch,
    summarize_paper,
)


def test_extract_json_plain_and_fenced():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('前言 {"a": {"b": 2}} 后记') == {"a": {"b": 2}}


def test_extract_json_rejects_garbage():
    with pytest.raises(ValueError):
        extract_json("完全没有 JSON")


def test_parse_summary_validates_fields():
    s = parse_summary('{"one_line": "做了X", "why_care": "因为Y", "relevance": 4}')
    assert s == Summary("做了X", "因为Y", 4)
    with pytest.raises(ValueError):
        parse_summary('{"one_line": "x", "why_care": "y", "relevance": 9}')
    with pytest.raises(ValueError):
        parse_summary('{"one_line": "", "why_care": "y", "relevance": 3}')


def test_summarize_paper_retries_then_succeeds():
    client = ScriptedClient(
        responses=["not json at all", '{"one_line": "A", "why_care": "B", "relevance": 5}']
    )
    s = summarize_paper(client, PaperStub("1"))
    assert s is not None and s.relevance == 5
    assert client.calls == 2


def test_summarize_paper_gives_up_after_bad_retry():
    client = ScriptedClient(responses=["bad", "still bad"])
    assert summarize_paper(client, PaperStub("1")) is None
    assert client.calls == 2


def test_summarize_batch_collects_and_skips_failures():
    client = ScriptedClient(
        responses=[
            '{"one_line": "A", "why_care": "B", "relevance": 5}',  # ok
            "junk", "junk again",  # paper 2 fails both tries
            '{"one_line": "C", "why_care": "D", "relevance": 2}',  # ok
        ]
    )
    out = summarize_batch(client, [PaperStub("1"), PaperStub("2"), PaperStub("3")])
    assert set(out) == {"1", "3"}
    assert out["1"].relevance == 5
