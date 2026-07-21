from datetime import date

from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import CAP_HOLDINGS
from pallisade_research.sources.holdings import HoldingsSource

ROWS = [
    {"ticker": "AAPL", "units": 100, "value": 25000, "as_of": "2026-06-20"},
    {"ticker": "NPN.JO", "units": 50, "value": 4275000, "as_of": "2026-06-20"},
]


def test_holdings_filters_by_ticker():
    src = HoldingsSource(ROWS)
    recs = src.fetch(ResearchQuery(question="q", ticker="AAPL", capabilities=(CAP_HOLDINGS,)))
    assert len(recs) == 1
    assert recs[0].capability == CAP_HOLDINGS
    assert recs[0].value == {"units": 100, "value": 25000}
    assert recs[0].provenance.source == "holdings"
    assert recs[0].provenance.as_of == date(2026, 6, 20)


def test_holdings_all_rows_when_ticker_none():
    src = HoldingsSource(ROWS)
    recs = src.fetch(ResearchQuery(question="q", ticker=None, capabilities=(CAP_HOLDINGS,)))
    assert {r.provenance.locator for r in recs} == {"holdings://AAPL", "holdings://NPN.JO"}
