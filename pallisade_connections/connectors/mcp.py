from __future__ import annotations

import asyncio
import hashlib
from typing import Callable

import httpx

from pallisade_connections.base import CAPABILITIES, FieldSpec, TestResult
from pallisade_research.models import Provenance, Record, ResearchQuery

ENDPOINT_FIELD: FieldSpec = {
    "name": "endpoint_url", "label": "MCP server URL", "kind": "text", "required": True,
}

# httpx.TransportError is the base of ConnectError/ConnectTimeout/ReadTimeout/
# NetworkError etc. It does NOT include HTTPStatusError, so a real 401 still
# correctly falls through to the auth branch below.
_NETWORK_ERRORS = (ConnectionError, TimeoutError, OSError, httpx.TransportError)


def _is_network_error(exc: BaseException) -> bool:
    """True if exc (or, for an ExceptionGroup, any contained leaf) is a transport/network failure."""
    if isinstance(exc, _NETWORK_ERRORS):
        return True
    # Python 3.11+ ExceptionGroup / anyio wraps transport errors from the mcp SDK's TaskGroup
    inner = getattr(exc, "exceptions", None)
    if inner:
        return any(_is_network_error(e) for e in inner)
    return False


def _root_detail(exc: BaseException) -> str:
    """A concise message: the first network/leaf cause if present, else str(exc)."""
    inner = getattr(exc, "exceptions", None)
    if inner:
        for e in inner:
            leaf = _root_detail(e)
            if leaf:
                return leaf
    return str(exc) or exc.__class__.__name__


def _default_probe(endpoint_url: str, creds: str | None) -> list[str]:
    """Connect to an MCP server over streamable HTTP and list tool names."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"Authorization": f"Bearer {creds}"} if creds else None

    async def _run() -> list[str]:
        async with streamablehttp_client(endpoint_url, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [t.name for t in tools.tools]

    return asyncio.run(_run())


def _default_fetch_tool(endpoint_url: str, creds: str | None, ticker: str) -> list[dict]:
    """Call a conventional research tool on the MCP server for a ticker.

    v1 convention: prefer a tool literally named 'research' or the first tool;
    pass {'symbol': ticker}. Returns a list of {title,url,capability} dicts.
    Real servers vary; this default handles the common shape and returns [] on
    anything it cannot interpret.
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"Authorization": f"Bearer {creds}"} if creds else None

    async def _run() -> list[dict]:
        async with streamablehttp_client(endpoint_url, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                if not tools:
                    return []
                name = next((t.name for t in tools if "research" in t.name.lower()), tools[0].name)
                result = await session.call_tool(name, {"symbol": ticker})
                out: list[dict] = []
                for block in result.content:
                    text = getattr(block, "text", None)
                    if text:
                        out.append({"title": text[:280], "url": endpoint_url, "capability": "research"})
                return out

    return asyncio.run(_run())


class McpResearchSource:
    source = "mcp"
    capabilities = frozenset(CAPABILITIES)

    def __init__(self, endpoint_url: str, creds: str | None, fetch_tool: Callable):
        self._endpoint = endpoint_url
        self._creds = creds
        self._fetch = fetch_tool

    def fetch(self, query: ResearchQuery) -> list[Record]:
        if query.ticker is None:
            return []
        rows = self._fetch(self._endpoint, self._creds, query.ticker)
        ep = hashlib.sha1(self._endpoint.encode()).hexdigest()[:8]
        out: list[Record] = []
        for i, row in enumerate(rows):
            out.append(Record(
                id=f"mcp-{ep}-{query.ticker}-{i}",
                capability=row.get("capability", "research"),
                key=f"mcp.{i}",
                value=row.get("title", ""),
                provenance=Provenance(source="mcp", locator=row.get("url", self._endpoint),
                                      as_of=None, detail="MCP server"),
            ))
        return out


class McpConnector:
    type_id = "mcp"
    requires_credentials = True
    config_fields = [ENDPOINT_FIELD]
    capabilities = frozenset(CAPABILITIES)

    def __init__(self, probe: Callable[[str, str | None], list[str]] | None = None,
                 fetch_tool: Callable | None = None):
        self._probe = probe or _default_probe
        self._fetch_tool = fetch_tool or _default_fetch_tool

    def test(self, creds, config) -> TestResult:
        url = (config or {}).get("endpoint_url")
        if not url:
            return {"ok": False, "kind": "unsupported", "detail": "MCP server URL is required."}
        try:
            tools = self._probe(url, creds)
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:  # includes ExceptionGroup from the mcp SDK's anyio TaskGroup
            if _is_network_error(exc):
                return {"ok": False, "kind": "network", "detail": f"Could not reach server: {_root_detail(exc)}"}
            return {"ok": False, "kind": "auth", "detail": f"Server rejected connection: {_root_detail(exc)}"}
        return {"ok": True, "kind": "ok", "detail": f"Connected — {len(tools)} tool(s) available."}

    def as_research_source(self, creds, config):
        return McpResearchSource((config or {}).get("endpoint_url", ""), creds, self._fetch_tool)
