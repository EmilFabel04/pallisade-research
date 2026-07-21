from __future__ import annotations

import httpx

from pallisade_connections.connectors.mcp import McpConnector
from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import ResearchSource


def test_mcp_test_ok_with_fake_probe():
    c = McpConnector(probe=lambda url, creds: ["get_fundamentals", "get_news"])
    res = c.test("key", {"endpoint_url": "https://mcp.example/x"})
    assert res["ok"] is True and res["kind"] == "ok"
    assert "2 tool" in res["detail"]


def test_mcp_test_missing_url():
    c = McpConnector(probe=lambda url, creds: [])
    res = c.test("key", {})
    assert res["ok"] is False and res["kind"] == "unsupported"


def test_mcp_test_network_failure():
    def boom(url, creds):
        raise ConnectionError("refused")
    c = McpConnector(probe=boom)
    res = c.test("key", {"endpoint_url": "https://x"})
    assert res["ok"] is False and res["kind"] == "network"


def test_mcp_source_maps_tool_output_to_records():
    # fetch_tool returns a list of dicts; source wraps them as Records
    def fake_fetch(endpoint, creds, ticker):
        return [{"title": "Rev beat", "url": "https://mcp/x/1", "capability": "news"}]
    c = McpConnector(probe=lambda url, creds: ["x"], fetch_tool=fake_fetch)
    src = c.as_research_source("key", {"endpoint_url": "https://x"})
    assert isinstance(src, ResearchSource)
    recs = src.fetch(ResearchQuery(question="q", ticker="AAPL", capabilities=("news",)))
    assert len(recs) == 1
    assert recs[0].value == "Rev beat"
    assert recs[0].provenance.source == "mcp"


def test_mcp_test_httpx_network_failure_is_network():
    def boom(url, creds):
        raise httpx.ConnectError("refused")
    c = McpConnector(probe=boom)
    res = c.test("key", {"endpoint_url": "https://x"})
    assert res["ok"] is False and res["kind"] == "network"


def test_mcp_test_generic_error_is_auth():
    def boom(url, creds):
        raise ValueError("bad token")
    c = McpConnector(probe=boom)
    res = c.test("key", {"endpoint_url": "https://x"})
    assert res["ok"] is False and res["kind"] == "auth"


def test_mcp_exception_group_network_is_network():
    # Mirrors how the real mcp SDK's streamablehttp_client (anyio TaskGroup)
    # surfaces a DNS/connect failure: wrapped in an ExceptionGroup, not a bare
    # httpx.TransportError.
    def boom(url, creds):
        raise ExceptionGroup("boom", [httpx.ConnectError("dns fail")])
    c = McpConnector(probe=boom)
    res = c.test("key", {"endpoint_url": "https://x"})
    assert res["ok"] is False and res["kind"] == "network"
    assert "dns fail" in res["detail"]
    assert "TaskGroup" not in res["detail"]


def test_mcp_exception_group_generic_is_auth():
    def boom(url, creds):
        raise ExceptionGroup("boom", [ValueError("bad token")])
    c = McpConnector(probe=boom)
    res = c.test("key", {"endpoint_url": "https://x"})
    assert res["ok"] is False and res["kind"] == "auth"


def test_mcp_record_ids_are_unique_per_row():
    def fake_fetch(endpoint, creds, ticker):
        return [
            {"title": "Rev beat", "url": "https://mcp/x/1", "capability": "news"},
            {"title": "Guidance cut", "url": "https://mcp/x/2", "capability": "news"},
        ]
    c = McpConnector(probe=lambda url, creds: ["x"], fetch_tool=fake_fetch)
    src = c.as_research_source("key", {"endpoint_url": "https://x"})
    recs = src.fetch(ResearchQuery(question="q", ticker="AAPL", capabilities=("news",)))
    assert len(recs) == 2
    ids = [r.id for r in recs]
    assert len(set(ids)) == 2
    for rid in ids:
        assert "AAPL" in rid
