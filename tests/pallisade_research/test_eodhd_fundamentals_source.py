from datetime import date

from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import CAP_METRICS
from pallisade_research.sources.eodhd_fundamentals import EODHDFundamentalsSource

_FUNDAMENTALS = {
    "Financials": {
        "Income_Statement": {
            "yearly": {
                "2025-12-31": {"date": "2025-12-31", "totalRevenue": "120", "netIncome": "24", "epsActual": "1.2"},
                "2024-12-31": {"date": "2024-12-31", "totalRevenue": "100", "netIncome": "18", "epsActual": "1.0"},
                "2023-12-31": {"date": "2023-12-31", "totalRevenue": "80", "netIncome": "12", "epsActual": "0.8"},
                "2022-12-31": {"date": "2022-12-31", "totalRevenue": "NA", "netIncome": "NA", "epsActual": "NA"},
            }
        }
    }
}


def _query(ticker="AAPL"):
    return ResearchQuery(question="has AAPL revenue grown?", ticker=ticker, capabilities=(CAP_METRICS,))


def test_emits_series_records_oldest_to_newest():
    src = EODHDFundamentalsSource(http_get=lambda url, params: _FUNDAMENTALS, api_key="k")
    recs = src.fetch(_query())
    by_key = {r.key: r for r in recs}
    rev = by_key["metrics.revenue.series"]
    assert rev.capability == CAP_METRICS
    assert rev.evidence_only is True
    assert rev.provenance.source == "eodhd_fundamentals"
    assert rev.value == ((date(2023, 12, 31), 80.0), (date(2024, 12, 31), 100.0), (date(2025, 12, 31), 120.0))
    assert rev.provenance.as_of == date(2025, 12, 31)


def test_drops_na_points_and_omits_short_series():
    # net_income has 3 valid points -> present; a metric with <2 valid points is omitted.
    src = EODHDFundamentalsSource(http_get=lambda url, params: _FUNDAMENTALS, api_key="k")
    keys = {r.key for r in src.fetch(_query())}
    assert "metrics.net_income.series" in keys
    assert "metrics.revenue.series" in keys


def test_no_key_returns_empty():
    src = EODHDFundamentalsSource(http_get=lambda url, params: _FUNDAMENTALS, api_key="")
    assert src.fetch(_query()) == []


def test_unmapped_ticker_returns_empty():
    src = EODHDFundamentalsSource(http_get=lambda url, params: _FUNDAMENTALS, api_key="k")
    assert src.fetch(_query(ticker="XYZ.ZZ")) == []


def test_transport_error_returns_empty():
    def boom(url, params):
        raise RuntimeError("network down")
    src = EODHDFundamentalsSource(http_get=boom, api_key="k")
    assert src.fetch(_query()) == []


def test_non_dict_payload_returns_empty():
    src = EODHDFundamentalsSource(http_get=lambda url, params: [], api_key="k")
    assert src.fetch(_query()) == []
