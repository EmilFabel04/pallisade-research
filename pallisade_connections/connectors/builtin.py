from __future__ import annotations

import os

from pallisade_connections.base import FieldSpec, TestResult
from pallisade_research.sources.eodhd import EODHDSource
from pallisade_research.sources.eodhd_markets import EODHDMarketsSource
from pallisade_research.sources.holdings import HoldingsSource
from pallisade_research.sources.smartkarma import SmartkarmaSource
from pallisade_research.sources.worldbank import WorldBankSource
from pallisade_research.sources.yfinance_source import YFinanceSource


class YFinanceConnector:
    type_id = "yfinance"
    requires_credentials = False
    config_fields: list[FieldSpec] = []
    capabilities = frozenset({"prices", "fundamentals", "news"})

    def test(self, creds, config) -> TestResult:
        return {"ok": True, "kind": "ok", "detail": "Built-in free source; always available."}

    def as_research_source(self, creds, config):
        return YFinanceSource()


class EODHDConnector:
    type_id = "eodhd"
    requires_credentials = False  # shared platform key from env, not per-user
    config_fields: list[FieldSpec] = []
    capabilities = frozenset({"news"})

    def test(self, creds, config) -> TestResult:
        if not os.environ.get("EODHD_API_KEY"):
            return {"ok": False, "kind": "unsupported", "detail": "Set EODHD_API_KEY in the platform environment."}
        return {"ok": True, "kind": "ok", "detail": "Built-in worldwide news via shared EODHD key."}

    def as_research_source(self, creds, config):
        return EODHDSource()


class EODHDMarketsConnector:
    type_id = "eodhd_markets"
    requires_credentials = False  # shared platform key from env, not per-user
    config_fields: list[FieldSpec] = []
    capabilities = frozenset({"markets"})

    def test(self, creds, config) -> TestResult:
        if not os.environ.get("EODHD_API_KEY"):
            return {"ok": False, "kind": "unsupported", "detail": "Set EODHD_API_KEY in the platform environment."}
        return {"ok": True, "kind": "ok", "detail": "Built-in FX/crypto/index via shared EODHD key."}

    def as_research_source(self, creds, config):
        return EODHDMarketsSource()


class WorldBankConnector:
    type_id = "worldbank"
    requires_credentials = False
    config_fields: list[FieldSpec] = []
    capabilities = frozenset({"macro"})

    def test(self, creds, config) -> TestResult:
        return {"ok": True, "kind": "ok", "detail": "Built-in free any-country macro (World Bank)."}

    def as_research_source(self, creds, config):
        return WorldBankSource()


class SmartkarmaConnector:
    type_id = "smartkarma"
    requires_credentials = True
    config_fields: list[FieldSpec] = []
    capabilities = frozenset({"research"})

    def test(self, creds, config) -> TestResult:
        if not creds:
            return {"ok": False, "kind": "auth", "detail": "Smartkarma API key required."}
        return {"ok": True, "kind": "ok", "detail": "Key stored. Live probe runs on first query."}

    def as_research_source(self, creds, config):
        return SmartkarmaSource(api_key=creds or "")


class HoldingsConnector:
    type_id = "holdings"
    requires_credentials = False
    config_fields: list[FieldSpec] = []
    capabilities = frozenset({"holdings"})

    def test(self, creds, config) -> TestResult:
        rows = config.get("rows") or []
        if not rows:
            return {"ok": False, "kind": "unsupported", "detail": "No holdings rows uploaded yet."}
        return {"ok": True, "kind": "ok", "detail": f"{len(rows)} holdings rows."}

    def as_research_source(self, creds, config):
        return HoldingsSource(config.get("rows") or [])


class _NoopWebSource:
    """Placeholder so the web connector satisfies the source protocol.

    The real web research runs as an LLM loop in the converse layer, not as a
    fetch()-shaped source, so this never returns records."""

    source = "web"
    tier = 3
    capabilities = frozenset({"news", "research", "estimates", "transcripts"})

    def fetch(self, query):
        return []


class WebConnector:
    type_id = "web"
    requires_credentials = False
    config_fields: list[FieldSpec] = []
    capabilities = frozenset({"news", "research", "estimates", "transcripts"})

    def test(self, creds, config) -> TestResult:
        if not os.environ.get("WEB_SEARCH_API_KEY"):
            return {"ok": False, "kind": "unsupported", "detail": "Set WEB_SEARCH_API_KEY in the platform environment."}
        return {"ok": True, "kind": "ok", "detail": "Built-in grounded web research (shared search key)."}

    def as_research_source(self, creds, config):
        return _NoopWebSource()
