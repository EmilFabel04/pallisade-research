import importlib

import pytest

from tradingagents.agents.utils.documents_tool import search_org_documents

# Only the three tool-calling analysts are wired with search_org_documents.
# Excluded: sentiment_analyst does not use tool-calling (data is prompt-stuffed via single LLM call,
# no bind_tools), and social_media_analyst is a deprecated back-compat shim re-exporting sentiment.
# Wiring them would require converting sentiment to a tool-calling agent and registering
# search_org_documents in the graph's "social" ToolNode (deferred by decision).
ANALYST_MODULES = [
    "tradingagents.agents.analysts.fundamentals_analyst",
    "tradingagents.agents.analysts.market_analyst",
    "tradingagents.agents.analysts.news_analyst",
]


def test_tool_name_contract():
    assert search_org_documents.name == "search_org_documents"


@pytest.mark.parametrize("modpath", ANALYST_MODULES)
def test_analyst_module_imports_docs_tool(modpath):
    mod = importlib.import_module(modpath)
    assert getattr(mod, "search_org_documents", None) is search_org_documents
