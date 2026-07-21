"""Graph-level guard: the docs tool must be *executable*, not just bound.

The three tool-calling analysts (fundamentals, market, news) bind
``search_org_documents`` in their ``bind_tools(...)`` lists and are instructed
to call it first. But in LangGraph, tool *execution* happens in the ToolNode
for each category, not from the analyst's bound list — a tool call for a name
the ToolNode doesn't know returns a "not a valid tool" error instead of
running. This test builds the real ToolNodes via
``TradingAgentsGraph._create_tool_nodes`` and asserts ``search_org_documents``
is actually registered in each of the three ToolNodes it needs to be in.

``_create_tool_nodes`` doesn't reference ``self`` at all (it only wires
module-level tool functions into ``ToolNode`` instances), so it can be called
unbound on the class without constructing a full ``TradingAgentsGraph`` —
no LLM client, no network calls, no config needed.
"""

from tradingagents.agents.utils.documents_tool import search_org_documents
from tradingagents.graph.trading_graph import TradingAgentsGraph

DOCS_TOOL_NAME = "search_org_documents"


def _build_tool_nodes():
    # Unbound call: _create_tool_nodes takes `self` but never touches it.
    return TradingAgentsGraph._create_tool_nodes(None)


def test_tool_name_matches_module_export():
    assert search_org_documents.name == DOCS_TOOL_NAME


def test_market_toolnode_has_docs_tool():
    nodes = _build_tool_nodes()
    assert DOCS_TOOL_NAME in nodes["market"].tools_by_name


def test_news_toolnode_has_docs_tool():
    nodes = _build_tool_nodes()
    assert DOCS_TOOL_NAME in nodes["news"].tools_by_name


def test_fundamentals_toolnode_has_docs_tool():
    nodes = _build_tool_nodes()
    assert DOCS_TOOL_NAME in nodes["fundamentals"].tools_by_name


def test_social_toolnode_excludes_docs_tool():
    # Sentiment/social analysts are intentionally excluded from docs wiring
    # (see tests/pallisade/test_analyst_has_docs_tool.py for rationale).
    nodes = _build_tool_nodes()
    assert DOCS_TOOL_NAME not in nodes["social"].tools_by_name
