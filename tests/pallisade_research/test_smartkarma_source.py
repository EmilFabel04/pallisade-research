from datetime import date

from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import CAP_RESEARCH
from pallisade_research.sources.smartkarma import SmartkarmaSource

FIXTURE = {
    "insights": [
        {"id": "i1", "title": "Naspers: Prosus discount narrows", "url": "https://smartkarma.com/insights/i1", "published": "2026-06-18"},
        {"id": "i2", "title": "Tencent read-through to NPN", "url": "https://smartkarma.com/insights/i2", "published": "2026-06-10"},
    ]
}


def test_smartkarma_maps_insights_to_records():
    captured = {}

    def fake_get(url, params):
        captured["url"] = url
        captured["params"] = params
        return FIXTURE

    src = SmartkarmaSource(http_get=fake_get, api_key="k")
    recs = src.fetch(ResearchQuery(question="q", ticker="NPN.JO", capabilities=(CAP_RESEARCH,)))
    assert len(recs) == 2
    assert recs[0].capability == CAP_RESEARCH
    assert recs[0].provenance.locator == "https://smartkarma.com/insights/i1"
    assert recs[0].provenance.as_of == date(2026, 6, 18)
    assert captured["params"]["symbol"] == "NPN.JO"


def test_smartkarma_empty_on_no_insights():
    src = SmartkarmaSource(http_get=lambda url, params: {"insights": []}, api_key="k")
    recs = src.fetch(ResearchQuery(question="q", ticker="AAPL", capabilities=(CAP_RESEARCH,)))
    assert recs == []
