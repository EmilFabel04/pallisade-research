from datetime import date

from pallisade_research.models import (
    Claim,
    CitedAnswer,
    CoverageGap,
    Provenance,
    Record,
    ResearchQuery,
)


def test_record_carries_provenance():
    rec = Record(
        id="r1",
        capability="fundamentals",
        key="revenue.fy2024",
        value=55_000_000_000,
        provenance=Provenance(source="yfinance", locator="https://x/AAPL", as_of=date(2024, 12, 31)),
    )
    assert rec.provenance.source == "yfinance"
    assert rec.provenance.detail == ""  # optional default


def test_claim_requires_record_ids():
    claim = Claim(text="Revenue FY2024 was R55bn", record_ids=("r1", "r2"))
    assert claim.record_ids == ("r1", "r2")


def test_cited_answer_assembles():
    ans = CitedAnswer(
        question="overview of AAPL",
        claims=(Claim(text="x", record_ids=("r1",)),),
        records=(),
        gaps=(CoverageGap(note="No news coverage"),),
        sources_used=("yfinance",),
        sources_unavailable=("factset",),
    )
    assert ans.sources_unavailable == ("factset",)
    assert isinstance(ResearchQuery(question="q", ticker="AAPL", capabilities=("news",)).capabilities, tuple)


def test_research_query_carries_entity():
    q = ResearchQuery(question="Nigeria GDP", ticker=None, capabilities=("macro",),
                      entity="Nigeria", entity_type="country")
    assert q.entity == "Nigeria" and q.entity_type == "country"


def test_research_query_entity_defaults_none():
    q = ResearchQuery(question="q", ticker="AAPL", capabilities=("fundamentals",))
    assert q.entity is None and q.entity_type is None


def test_new_capabilities_registered():
    from pallisade_research.sources.base import ALL_CAPABILITIES, CAP_MACRO, CAP_MARKETS
    assert CAP_MACRO == "macro" and CAP_MARKETS == "markets"
    assert {"macro", "markets"} <= ALL_CAPABILITIES
