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


def test_profit_margin_and_eps_series_computed():
    src = EODHDFundamentalsSource(http_get=lambda url, params: _FUNDAMENTALS, api_key="k")
    recs = src.fetch(_query())
    by_key = {r.key: r for r in recs}

    # EPS series: directly copied from payload
    eps = by_key["metrics.eps.series"]
    assert eps.value == ((date(2023, 12, 31), 0.8), (date(2024, 12, 31), 1.0), (date(2025, 12, 31), 1.2))
    assert eps.provenance.as_of == date(2025, 12, 31)

    # Profit margin series: derived as (net_income / revenue) * 100
    # 2023: 12/80 * 100 = 15.0
    # 2024: 18/100 * 100 = 18.0
    # 2025: 24/120 * 100 = 20.0
    pm = by_key["metrics.profit_margin.series"]
    assert pm.value == ((date(2023, 12, 31), 15.0), (date(2024, 12, 31), 18.0), (date(2025, 12, 31), 20.0))
    assert pm.provenance.as_of == date(2025, 12, 31)


def test_profit_margin_skips_zero_revenue_row():
    # Payload with a zero-revenue row where netIncome is non-NA
    fake_payload = {
        "Financials": {
            "Income_Statement": {
                "yearly": {
                    "2025-12-31": {"date": "2025-12-31", "totalRevenue": "100", "netIncome": "18", "epsActual": "1.0"},
                    "2024-12-31": {"date": "2024-12-31", "totalRevenue": "0", "netIncome": "10", "epsActual": "0.8"},
                    "2023-12-31": {"date": "2023-12-31", "totalRevenue": "80", "netIncome": "12", "epsActual": "0.6"},
                }
            }
        }
    }

    src = EODHDFundamentalsSource(http_get=lambda url, params: fake_payload, api_key="k")
    recs = src.fetch(_query())
    by_key = {r.key: r for r in recs}

    # net_income should include all three years (guard doesn't apply to net_income)
    ni = by_key["metrics.net_income.series"]
    assert ni.value == ((date(2023, 12, 31), 12.0), (date(2024, 12, 31), 10.0), (date(2025, 12, 31), 18.0))

    # profit_margin should skip the zero-revenue year (2024)
    # 2023: 12/80 * 100 = 15.0
    # 2025: 18/100 * 100 = 18.0
    pm = by_key["metrics.profit_margin.series"]
    assert pm.value == ((date(2023, 12, 31), 15.0), (date(2025, 12, 31), 18.0))
