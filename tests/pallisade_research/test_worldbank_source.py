from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import CAP_MACRO
from pallisade_research.sources.worldbank import WorldBankSource, to_iso2


def _wb_ok(value, date, cname):
    return [{"page": 1}, [{"value": value, "date": date, "country": {"value": cname},
                           "indicator": {"value": "x"}}]]


def test_iso2_mapping():
    assert to_iso2("Nigeria") == "NG"
    assert to_iso2("south africa") == "ZA"
    assert to_iso2("United States") == "US"
    assert to_iso2("NG") == "NG"          # already a code
    assert to_iso2("Atlantis") is None


def test_worldbank_returns_macro_records():
    calls = []

    def fake_get(url, params):
        calls.append(url)
        return _wb_ok(290.0, "2025", "Nigeria")

    src = WorldBankSource(http_get=fake_get)
    recs = src.fetch(ResearchQuery(question="Nigeria GDP", ticker=None,
                     capabilities=(CAP_MACRO,), entity="Nigeria", entity_type="country"))
    assert recs and all(r.capability == CAP_MACRO for r in recs)
    assert any("NG" in u for u in calls)
    assert recs[0].provenance.source == "worldbank"


def test_worldbank_noop_when_not_country():
    src = WorldBankSource(http_get=lambda u, p: _wb_ok(1, "2025", "x"))
    assert src.fetch(ResearchQuery(question="q", ticker="AAPL",
                     capabilities=(CAP_MACRO,), entity=None, entity_type=None)) == []
    assert src.fetch(ResearchQuery(question="q", ticker=None, capabilities=(CAP_MACRO,),
                     entity="Atlantis", entity_type="country")) == []


def test_worldbank_tolerates_indicator_error():
    def flaky(url, params):
        if "FP.CPI" in url:
            raise TimeoutError("boom")
        return _wb_ok(1.0, "2025", "Nigeria")

    src = WorldBankSource(http_get=flaky)
    recs = src.fetch(ResearchQuery(question="q", ticker=None, capabilities=(CAP_MACRO,),
                     entity="Nigeria", entity_type="country"))
    assert recs  # other indicators still returned
