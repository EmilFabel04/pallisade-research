from pallisade_research.engine import answer
from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_FUNDAMENTALS, CAP_RESEARCH
from pallisade_research.sources.registry import ClientConfig


class _Src:
    def __init__(self, name, caps, recs):
        self.source = name
        self.capabilities = frozenset(caps)
        self._recs = recs

    def fetch(self, query):
        return self._recs


class _Boom:
    source = "factset"
    capabilities = frozenset({CAP_FUNDAMENTALS})

    def fetch(self, query):
        raise RuntimeError("entitlement missing")


def _rec(rid, source, key, value, cap=CAP_FUNDAMENTALS):
    return Record(id=rid, capability=cap, key=key, value=value,
                  provenance=Provenance(source=source, locator=f"l/{rid}", as_of=None))


def test_engine_cross_source_cites_both_and_lists_used():
    registry = {
        "yfinance": _Src("yfinance", {CAP_FUNDAMENTALS}, [_rec("r1", "yfinance", "fundamentals.rev", 55)]),
        "smartkarma": _Src("smartkarma", {CAP_RESEARCH}, [_rec("r2", "smartkarma", "research.i1", "note", CAP_RESEARCH)]),
    }
    config = ClientConfig(client_id="acme", enabled_sources=frozenset({"yfinance", "smartkarma"}))
    q = ResearchQuery(question="overview", ticker="AAPL", capabilities=(CAP_FUNDAMENTALS, CAP_RESEARCH))
    ans = answer(q, config, registry)
    assert set(ans.sources_used) == {"yfinance", "smartkarma"}
    assert len(ans.records) == 2
    assert all(c.record_ids for c in ans.claims)  # every claim cited


def test_engine_records_unavailable_source_without_crashing():
    registry = {
        "factset": _Boom(),
        "yfinance": _Src("yfinance", {CAP_FUNDAMENTALS}, [_rec("r1", "yfinance", "fundamentals.rev", 55)]),
    }
    config = ClientConfig(client_id="acme", enabled_sources=frozenset({"factset", "yfinance"}))
    q = ResearchQuery(question="overview", ticker="AAPL", capabilities=(CAP_FUNDAMENTALS,))
    ans = answer(q, config, registry)
    assert ans.sources_unavailable == ("factset",)
    assert ans.sources_used == ("yfinance",)


def test_engine_emits_gap_for_uncovered_capability():
    registry = {"yfinance": _Src("yfinance", {CAP_FUNDAMENTALS}, [_rec("r1", "yfinance", "fundamentals.rev", 55)])}
    config = ClientConfig(client_id="acme", enabled_sources=frozenset({"yfinance"}))
    q = ResearchQuery(question="overview", ticker="AAPL", capabilities=(CAP_FUNDAMENTALS, "news"))
    ans = answer(q, config, registry)
    assert any("news" in g.note for g in ans.gaps)


def test_fundamentals_gap_still_returns_news_context():
    from pallisade_research.sources.base import CAP_NEWS
    from pallisade_research.sources.eodhd import EODHDSource

    class _NoFundamentals:
        source = "stub_fund"
        tier = 3
        capabilities = frozenset({CAP_FUNDAMENTALS})

        def fetch(self, query):
            return []

    news = [{"date": "2026-06-18T00:00:00+00:00", "title": "Company X news", "link": "https://x/a"}]
    registry = {
        "stub_fund": _NoFundamentals(),
        "eodhd": EODHDSource(http_get=lambda u, p: news, api_key="k"),
    }
    config = ClientConfig(client_id="org", enabled_sources=frozenset(registry))
    result = answer(
        ResearchQuery(question="is X worth holding?", ticker="X",
                      capabilities=(CAP_FUNDAMENTALS, CAP_NEWS)),
        config, registry,
    )
    # gap for the uncovered fundamentals capability
    assert any("fundamentals" in g.note for g in result.gaps)
    # but news context still comes back
    assert result.claims, "expected news claims as fallback context"
    assert "eodhd" in result.sources_used
