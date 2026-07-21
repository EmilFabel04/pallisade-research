from datetime import date

from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import CAP_NEWS
from pallisade_research.sources.eodhd import EODHDSource, to_eodhd_symbol

FIXTURE = [
    {"date": "2026-06-29T10:00:00+00:00", "title": "Prosus core earnings leap 84%",
     "link": "https://ex.com/a", "content": "…"},
    {"date": "2026-06-28T08:00:00+00:00", "title": "Naspers FY2026 earnings call",
     "link": "https://ex.com/b", "content": "…"},
]


def test_symbol_mapping():
    assert to_eodhd_symbol("NPN.JO") == "NPN.JSE"
    assert to_eodhd_symbol("005930.KS") == "005930.KO"
    assert to_eodhd_symbol("0700.HK") == "0700.HK"
    assert to_eodhd_symbol("AAPL") == "AAPL.US"
    assert to_eodhd_symbol("7203.T") is None  # Tokyo local — parked gap


def test_eodhd_maps_news_to_records():
    captured = {}

    def fake_get(url, params):
        captured["url"] = url
        captured["params"] = params
        return FIXTURE

    src = EODHDSource(http_get=fake_get, api_key="k")
    recs = src.fetch(ResearchQuery(question="news on Naspers", ticker="NPN.JO", capabilities=(CAP_NEWS,)))
    assert len(recs) == 2
    assert recs[0].capability == CAP_NEWS
    assert recs[0].value == "Prosus core earnings leap 84%"
    assert recs[0].provenance.source == "eodhd"
    assert recs[0].provenance.locator == "https://ex.com/a"
    assert recs[0].provenance.as_of == date(2026, 6, 29)
    assert captured["params"]["s"] == "NPN.JSE"
    assert captured["params"]["api_token"] == "k"


def test_eodhd_empty_without_key():
    src = EODHDSource(http_get=lambda u, p: FIXTURE, api_key="")
    recs = src.fetch(ResearchQuery(question="q", ticker="AAPL", capabilities=(CAP_NEWS,)))
    assert recs == []


def test_eodhd_empty_without_ticker_or_unmapped():
    src = EODHDSource(http_get=lambda u, p: FIXTURE, api_key="k")
    assert src.fetch(ResearchQuery(question="q", ticker=None, capabilities=(CAP_NEWS,))) == []
    assert src.fetch(ResearchQuery(question="q", ticker="7203.T", capabilities=(CAP_NEWS,))) == []
