from datetime import date
from pallisade_research.models import Provenance


def test_provenance_defaults_tier_3_live():
    p = Provenance(source="yfinance", locator="x", as_of=date(2026, 1, 1))
    assert p.tier == 3
    assert p.liveness == "live"


def test_provenance_accepts_tier_and_liveness():
    p = Provenance(source="documents", locator="f.xlsx", as_of=None, tier=1, liveness="static")
    assert p.tier == 1
    assert p.liveness == "static"
