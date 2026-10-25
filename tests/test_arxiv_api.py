from datetime import datetime

from arxiv_digest.arxiv_api import Paper, build_query, parse_atom

FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query</title>
  <entry>
    <id>http://arxiv.org/abs/2410.12345v1</id>
    <updated>2026-10-20T00:00:00Z</updated>
    <published>2026-10-20T12:00:00Z</published>
    <title> A Tool-Using\n  Agent   Framework </title>
    <summary>We  present a framework\nfor agents that call tools.</summary>
    <author><name>Alice  Chen</name></author>
    <author><name>Bob Li</name></author>
    <category term="cs.AI"/>
    <category term="cs.CL"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2410.99999v2</id>
    <published>2026-10-21T08:30:00Z</published>
    <title>Another   Paper</title>
    <summary>Second abstract.</summary>
    <author><name>Carol Wu</name></author>
    <category term="cs.LG"/>
  </entry>
</feed>
"""


def test_parse_atom_cleans_whitespace_and_reads_fields():
    papers = parse_atom(FIXTURE)
    assert len(papers) == 2
    p = papers[0]
    assert p.arxiv_id == "2410.12345v1"
    assert p.short_id == "2410.12345"
    assert p.title == "A Tool-Using Agent Framework"
    assert p.abstract == "We present a framework for agents that call tools."
    assert p.authors == ["Alice Chen", "Bob Li"]
    assert p.categories == ["cs.AI", "cs.CL"]
    assert p.published == datetime(2026, 10, 20, 12, 0)
    assert p.url == "https://arxiv.org/abs/2410.12345v1"
    assert p.first_author == "Alice Chen 等"


def test_build_query_format():
    q = build_query("cs.CL", datetime(2026, 10, 20), datetime(2026, 10, 23))
    assert q == "cat:cs.CL AND submittedDate:[202610200000 TO 202610230000]"


def test_short_id_strips_version():
    p = Paper(
        arxiv_id="2410.99999v2", title="t", authors=["a"], categories=["cs.LG"],
        abstract="x", published=datetime.min, url="u",
    )
    assert p.short_id == "2410.99999"
