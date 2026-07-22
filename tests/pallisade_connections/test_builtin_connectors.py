from __future__ import annotations

from pallisade_connections.connectors.builtin import (
    EODHDConnector, EODHDMarketsConnector, HoldingsConnector,
    SmartkarmaConnector, WorldBankConnector, YFinanceConnector,
)
from pallisade_research.sources.base import ResearchSource


def test_worldbank_keyless():
    c = WorldBankConnector()
    assert c.type_id == "worldbank" and c.requires_credentials is False and "macro" in c.capabilities
    assert c.test(None, {})["ok"] is True
    assert isinstance(c.as_research_source(None, {}), ResearchSource)


def test_eodhd_markets_connector(monkeypatch):
    monkeypatch.setenv("EODHD_API_KEY", "k")
    c = EODHDMarketsConnector()
    assert c.type_id == "eodhd_markets" and c.requires_credentials is False and "markets" in c.capabilities
    assert c.test(None, {})["ok"] is True
    assert isinstance(c.as_research_source(None, {}), ResearchSource)


def test_eodhd_is_ui_keyless_and_registers_source(monkeypatch):
    monkeypatch.setenv("EODHD_API_KEY", "k")
    c = EODHDConnector()
    assert c.type_id == "eodhd"
    assert c.requires_credentials is False
    assert "news" in c.capabilities
    res = c.test(None, {})
    assert res["ok"] is True and res["kind"] == "ok"
    assert isinstance(c.as_research_source(None, {}), ResearchSource)


def test_eodhd_test_reports_unsupported_without_platform_key(monkeypatch):
    monkeypatch.delenv("EODHD_API_KEY", raising=False)
    res = EODHDConnector().test(None, {})
    assert res["ok"] is False and res["kind"] == "unsupported"


def test_yfinance_is_keyless_and_always_ok():
    c = YFinanceConnector()
    assert c.requires_credentials is False
    res = c.test(None, {})
    assert res["ok"] is True and res["kind"] == "ok"
    assert isinstance(c.as_research_source(None, {}), ResearchSource)


def test_smartkarma_requires_key():
    c = SmartkarmaConnector()
    assert c.requires_credentials is True
    res = c.test(None, {})
    assert res["ok"] is False and res["kind"] == "auth"
    # with a key, it builds a source (no network in construction)
    assert isinstance(c.as_research_source("k", {}), ResearchSource)


def test_holdings_from_config_rows():
    c = HoldingsConnector()
    src = c.as_research_source(None, {"rows": [{"ticker": "AAPL", "units": 1, "value": 1, "as_of": "2026-06-20"}]})
    assert isinstance(src, ResearchSource)


def test_holdings_test_reports_unsupported_without_rows():
    c = HoldingsConnector()
    res = c.test(None, {})
    assert res["ok"] is False and res["kind"] == "unsupported"


def test_holdings_test_ok_with_rows():
    c = HoldingsConnector()
    res = c.test(None, {"rows": [{"ticker": "AAPL", "units": 1, "value": 1, "as_of": "2026-06-20"}]})
    assert res["ok"] is True and res["kind"] == "ok"


def test_smartkarma_test_ok_with_key():
    c = SmartkarmaConnector()
    res = c.test("some-key", {})
    assert res["ok"] is True and res["kind"] == "ok"


def test_eodhd_fundamentals_connector_registered_and_always_on():
    from pallisade_connections.registry import CONNECTOR_REGISTRY
    from pallisade_connections.resolver import BUILTIN_ALWAYS_ON
    from pallisade_research.sources.eodhd_fundamentals import EODHDFundamentalsSource

    conn = CONNECTOR_REGISTRY["eodhd_fundamentals"]
    assert conn.type_id == "eodhd_fundamentals"
    assert conn.requires_credentials is False
    assert conn.capabilities == frozenset({"metrics"})
    assert isinstance(conn.as_research_source(None, {}), EODHDFundamentalsSource)
    assert "eodhd_fundamentals" in BUILTIN_ALWAYS_ON
