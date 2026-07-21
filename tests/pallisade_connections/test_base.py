from __future__ import annotations

from pallisade_connections.base import CAPABILITIES, DEBATE_CATEGORY, Connector


def test_capabilities_include_expected():
    assert set(CAPABILITIES) >= {"prices", "fundamentals", "news", "research", "holdings"}


def test_debate_category_maps_known_caps():
    assert DEBATE_CATEGORY["fundamentals"] == "fundamental_data"
    assert DEBATE_CATEGORY["news"] == "news_data"
    assert DEBATE_CATEGORY["prices"] == "core_stock_apis"


def test_connector_is_runtime_checkable_protocol():
    # A minimal object with the right attrs/methods should duck-type as a Connector.
    class Fake:
        type_id = "fake"
        requires_credentials = False
        config_fields: list = []
        capabilities = frozenset({"news"})
        def test(self, creds, config):
            return {"ok": True, "kind": "ok", "detail": ""}
        def as_research_source(self, creds, config):
            return object()
    assert isinstance(Fake(), Connector)
