from __future__ import annotations

import pytest

from pallisade_connections.registry import CONNECTOR_REGISTRY, get_connector


def test_v1_connector_types_registered():
    assert set(CONNECTOR_REGISTRY) == {
        "yfinance", "eodhd", "eodhd_markets", "worldbank", "holdings", "smartkarma", "mcp",
    }


def test_get_connector_unknown_raises():
    with pytest.raises(KeyError):
        get_connector("nope")


def test_connectors_declare_capabilities():
    for c in CONNECTOR_REGISTRY.values():
        assert c.capabilities  # non-empty frozenset
        assert isinstance(c.type_id, str)
