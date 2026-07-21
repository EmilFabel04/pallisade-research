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
