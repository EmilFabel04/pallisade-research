from pallisade_research.models import Provenance, Record
from pallisade_research.reconcile import reconcile


def _rec(rid, source, key, value):
    return Record(id=rid, capability="fundamentals", key=key, value=value,
                  provenance=Provenance(source=source, locator=f"loc/{rid}", as_of=None))


def test_agreeing_sources_merge_into_one_claim_citing_both():
    recs = [
        _rec("r1", "yfinance", "fundamentals.revenue", 55),
        _rec("r2", "factset", "fundamentals.revenue", 55),
    ]
    claims = reconcile(recs)
    assert len(claims) == 1
    assert set(claims[0].record_ids) == {"r1", "r2"}


def test_disagreeing_sources_each_surface():
    recs = [
        _rec("r1", "yfinance", "fundamentals.revenue", 55),
        _rec("r2", "factset", "fundamentals.revenue", 57),
    ]
    claims = reconcile(recs)
    assert len(claims) == 2
    cited = {c.record_ids for c in claims}
    assert ("r1",) in cited and ("r2",) in cited


def test_distinct_keys_distinct_claims():
    recs = [
        _rec("r1", "yfinance", "fundamentals.revenue", 55),
        _rec("r2", "yfinance", "fundamentals.pe", 31),
    ]
    claims = reconcile(recs)
    assert len(claims) == 2


def test_reconcile_skips_evidence_only_but_keeps_derived():
    from datetime import date
    from pallisade_research.models import Derivation, Provenance, Record
    from pallisade_research.reconcile import reconcile
    from pallisade_research.sources.base import CAP_METRICS

    prov = Provenance(source="eodhd_fundamentals", locator="", as_of=None)
    series = Record(id="s1", capability=CAP_METRICS, key="metrics.revenue.series",
                    value=((date(2024, 12, 31), 100.0), (date(2025, 12, 31), 120.0)),
                    provenance=prov, evidence_only=True)
    derived = Record(id="s1-yoy", capability=CAP_METRICS, key="metrics.revenue.yoy",
                     value=20.0, provenance=prov,
                     derivation=Derivation("yoy", ("s1",), "YoY = ..."))
    claims = reconcile([series, derived])
    texts = [c.text for c in claims]
    assert any("metrics.revenue.yoy" in t for t in texts)
    assert not any("metrics.revenue.series" in t for t in texts)
