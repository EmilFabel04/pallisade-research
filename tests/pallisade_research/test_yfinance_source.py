from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import CAP_FUNDAMENTALS
from pallisade_research.sources.yfinance_source import YFinanceSource


def test_yfinance_maps_fundamentals_to_records():
    fake = lambda ticker: {"marketCap": 3_000_000_000_000, "trailingPE": 31.2}
    src = YFinanceSource(fetcher=fake)
    recs = src.fetch(ResearchQuery(question="q", ticker="AAPL", capabilities=(CAP_FUNDAMENTALS,)))
    by_key = {r.key: r.value for r in recs}
    assert by_key["fundamentals.marketCap"] == 3_000_000_000_000
    assert by_key["fundamentals.trailingPE"] == 31.2
    assert all(r.provenance.source == "yfinance" for r in recs)


def test_yfinance_returns_empty_without_ticker():
    src = YFinanceSource(fetcher=lambda t: {"x": 1})
    recs = src.fetch(ResearchQuery(question="q", ticker=None, capabilities=(CAP_FUNDAMENTALS,)))
    assert recs == []
