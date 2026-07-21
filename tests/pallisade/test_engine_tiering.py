from pallisade_research.engine import answer
from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.registry import ClientConfig


def _rec(rid, cap, val, source, tier):
    return Record(
        id=rid, capability=cap, key=f"{cap}.{rid}", value=val,
        provenance=Provenance(source=source, locator=rid, as_of=None, tier=tier),
    )


class _Src:
    def __init__(self, name, tier, recs, caps):
        self.source = name
        self.tier = tier
        self.capabilities = frozenset(caps)
        self._recs = recs

    def fetch(self, query):
        return self._recs


def test_higher_tier_suppresses_lower_for_same_capability():
    byok = _Src("byok", 2, [_rec("b1", "fundamentals", 10, "byok", 2)], ["fundamentals"])
    public = _Src("public", 3, [_rec("p1", "fundamentals", 11, "public", 3)], ["fundamentals"])
    registry = {"public": public, "byok": byok}
    cfg = ClientConfig(client_id="c", enabled_sources=frozenset(registry))
    q = ResearchQuery(question="q", ticker="AAPL", capabilities=("fundamentals",))
    result = answer(q, cfg, registry)
    ids = {r.id for r in result.records}
    assert ids == {"b1"}                 # public fundamentals suppressed by BYOK
    assert "byok" in result.sources_used
    assert "public" not in result.sources_used


def test_lower_tier_fills_uncovered_capability():
    byok = _Src("byok", 2, [_rec("b1", "fundamentals", 10, "byok", 2)], ["fundamentals"])
    public = _Src("public", 3, [_rec("p1", "news", "headline", "public", 3)], ["news"])
    registry = {"public": public, "byok": byok}
    cfg = ClientConfig(client_id="c", enabled_sources=frozenset(registry))
    q = ResearchQuery(question="q", ticker="AAPL", capabilities=("fundamentals", "news"))
    result = answer(q, cfg, registry)
    assert {r.id for r in result.records} == {"b1", "p1"}   # news not covered by BYOK, so public fills it
