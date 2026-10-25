from datetime import datetime

from arxiv_digest.arxiv_api import Paper
from arxiv_digest.state import SeenState


def mk(i: str) -> Paper:
    return Paper(
        arxiv_id=f"{i}v1", title=f"t{i}", authors=["a"], categories=["cs.AI"],
        abstract="x", published=datetime(2026, 10, 20), url=f"https://arxiv.org/abs/{i}",
    )


def test_roundtrip_and_filter(tmp_path):
    f = tmp_path / "state.json"
    st = SeenState.load(f)
    assert st.seen == {}

    st.mark_seen([mk("1"), mk("2")])
    st.save()

    st2 = SeenState.load(f)
    assert set(st2.seen) == {"1", "2"}
    new = st2.filter_new([mk("1"), mk("3")])
    assert [p.short_id for p in new] == ["3"]

    st2.mark_seen(new)
    st2.save()
    assert set(SeenState.load(f).seen) == {"1", "2", "3"}
