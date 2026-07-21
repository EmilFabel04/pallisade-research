from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_FUNDAMENTALS, CAP_NEWS
from pallisade_research.sources.registry import ClientConfig, resolve_sources


class _FakeSource:
    def __init__(self, name, caps):
        self.source = name
        self.capabilities = frozenset(caps)

    def fetch(self, query: ResearchQuery):
        return [Record(id=f"{self.source}-1", capability=CAP_FUNDAMENTALS, key="k",
                       value=1, provenance=Provenance(self.source, "loc", None))]


def test_resolve_only_returns_enabled_sources():
    registry = {
        "yfinance": _FakeSource("yfinance", {CAP_FUNDAMENTALS}),
        "smartkarma": _FakeSource("smartkarma", {CAP_NEWS}),
    }
    config = ClientConfig(client_id="acme", enabled_sources=frozenset({"yfinance"}))
    resolved = resolve_sources(config, registry)
    assert [s.source for s in resolved] == ["yfinance"]


def test_resolve_skips_unknown_enabled_names():
    registry = {"yfinance": _FakeSource("yfinance", {CAP_FUNDAMENTALS})}
    config = ClientConfig(client_id="acme", enabled_sources=frozenset({"yfinance", "ghost"}))
    resolved = resolve_sources(config, registry)
    assert [s.source for s in resolved] == ["yfinance"]
