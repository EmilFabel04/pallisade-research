from __future__ import annotations

from pallisade_connections.base import Connector
from pallisade_connections.connectors.builtin import (
    EODHDConnector, EODHDFundamentalsConnector, EODHDMarketsConnector, HoldingsConnector,
    SmartkarmaConnector, WebConnector, WorldBankConnector, YFinanceConnector,
)
from pallisade_connections.connectors.mcp import McpConnector

CONNECTOR_REGISTRY: dict[str, Connector] = {
    "yfinance": YFinanceConnector(),
    "eodhd": EODHDConnector(),
    "eodhd_markets": EODHDMarketsConnector(),
    "eodhd_fundamentals": EODHDFundamentalsConnector(),
    "worldbank": WorldBankConnector(),
    "holdings": HoldingsConnector(),
    "smartkarma": SmartkarmaConnector(),
    "web": WebConnector(),
    "mcp": McpConnector(),
}


def get_connector(type_id: str) -> Connector:
    return CONNECTOR_REGISTRY[type_id]
