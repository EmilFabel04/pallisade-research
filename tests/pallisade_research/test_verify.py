from pallisade_research.models import Claim, Provenance, Record
from pallisade_research.verify import verify


def _rec(rid, capability):
    return Record(id=rid, capability=capability, key=f"{capability}.k", value=1,
                  provenance=Provenance(source="s", locator="l", as_of=None))


def test_drops_claim_with_unknown_record_id():
    records = [_rec("r1", "fundamentals")]
    claims = [Claim(text="ok", record_ids=("r1",)), Claim(text="ghost", record_ids=("rX",))]
    kept, gaps = verify(claims, records, requested_capabilities=("fundamentals",))
    assert [c.text for c in kept] == ["ok"]
    assert gaps == []


def test_emits_coverage_gap_for_missing_capability():
    records = [_rec("r1", "fundamentals")]
    claims = [Claim(text="ok", record_ids=("r1",))]
    kept, gaps = verify(claims, records, requested_capabilities=("fundamentals", "news"))
    assert len(gaps) == 1
    assert "news" in gaps[0].note


def test_drops_claim_with_empty_record_ids():
    records = [_rec("r1", "fundamentals")]
    claims = [Claim(text="ungrounded", record_ids=())]
    kept, gaps = verify(claims, records, requested_capabilities=("fundamentals",))
    assert kept == []
