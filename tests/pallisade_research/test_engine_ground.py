from pallisade_research.engine import gather_structured, ground
from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_FUNDAMENTALS, CAP_RESEARCH
from pallisade_research.sources.registry import ClientConfig


class _Src:
    def __init__(self, name, caps, recs):
        self.source, self.capabilities, self._recs = name, frozenset(caps), recs

    def fetch(self, query):
        return self._recs


def _rec(rid, source, key, value, cap=CAP_FUNDAMENTALS):
    return Record(id=rid, capability=cap, key=key, value=value,
                  provenance=Provenance(source=source, locator=f"l/{rid}", as_of=None))


def test_gather_then_ground_matches_answer_shape():
    registry = {"yfinance": _Src("yfinance", {CAP_FUNDAMENTALS}, [_rec("r1", "yfinance", "fundamentals.rev", 55)])}
    config = ClientConfig(client_id="c", enabled_sources=frozenset({"yfinance"}))
    q = ResearchQuery(question="overview", ticker="AAPL", capabilities=(CAP_FUNDAMENTALS,))
    recs, used, unavail = gather_structured(q, config, registry)
    assert used == ["yfinance"] and unavail == []
    ans = ground(recs, q, used=used, unavailable=unavail)
    assert set(ans.sources_used) == {"yfinance"}
    assert all(c.record_ids for c in ans.claims)


def test_ground_merges_web_records_with_structured():
    q = ResearchQuery(question="news", ticker="AAPL", capabilities=(CAP_RESEARCH,))
    web = [_rec("w1", "web", "web.0", "Analyst raised estimates.", CAP_RESEARCH)]
    ans = ground(web, q, used=["web"], unavailable=[])
    assert "web" in ans.sources_used
    assert any("web" in c.text for c in ans.claims)
