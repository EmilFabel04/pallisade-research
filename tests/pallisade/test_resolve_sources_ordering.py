from pallisade_research.sources.registry import ClientConfig, resolve_sources


class _Src:
    def __init__(self, name, tier):
        self.source = name
        self.tier = tier
        self.capabilities = frozenset()

    def fetch(self, query):
        return []


def test_resolve_sources_orders_by_tier():
    registry = {
        "public": _Src("public", 3),
        "docs": _Src("docs", 1),
        "byok": _Src("byok", 2),
    }
    cfg = ClientConfig(client_id="c", enabled_sources=frozenset(registry))
    ordered = [s.source for s in resolve_sources(cfg, registry)]
    assert ordered == ["docs", "byok", "public"]


def test_resolve_sources_defaults_missing_tier_to_3():
    class NoTier:
        source = "legacy"
        capabilities = frozenset()

        def fetch(self, query):
            return []

    registry = {"legacy": NoTier(), "docs": _Src("docs", 1)}
    cfg = ClientConfig(client_id="c", enabled_sources=frozenset(registry))
    ordered = [s.source for s in resolve_sources(cfg, registry)]
    assert ordered == ["docs", "legacy"]
