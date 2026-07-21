"""Coverage for the free-text analysts' `**Takeaway**:` prompt line.

Mirrors the capture pattern in ``test_researcher_voice.py``: a recording
stub stands in for the LLM so we can inspect the system message actually
built by each analyst node, without hitting any network or real LLM.

``market``/``news``/``fundamentals`` analysts build their prompt via
``ChatPromptTemplate | llm.bind_tools(tools)``; the stub's ``bind_tools``
returns a ``RunnableLambda`` that records the rendered ``ChatPromptValue``
so we can read the system message text out of it.

``sentiment`` analyst has no tool-calling chain — it assembles the system
message via the module-level ``_build_system_message`` helper, which is
called directly here with fixture inputs (no network fetches involved).
"""

from types import SimpleNamespace

import pytest
from langchain_core.runnables import RunnableLambda

from tradingagents.agents.analysts.market_analyst import create_market_analyst
from tradingagents.agents.analysts.news_analyst import create_news_analyst
from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst
from tradingagents.agents.analysts.sentiment_analyst import _build_system_message


class RecordingToolLLM:
    """Stub LLM: `.bind_tools()` returns a Runnable that records the
    rendered prompt value instead of calling a real model."""

    def __init__(self):
        self.captured = None

    def bind_tools(self, tools):
        def _fn(prompt_value):
            self.captured = prompt_value
            return SimpleNamespace(content="report", tool_calls=[])

        return RunnableLambda(_fn)

    def system_message_text(self) -> str:
        return self.captured.messages[0].content


def _tool_state():
    return {
        "trade_date": "2026-01-01",
        "company_of_interest": "AAPL",
        "asset_type": "stock",
        "messages": [],
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    "factory",
    [create_market_analyst, create_news_analyst, create_fundamentals_analyst],
)
def test_tool_calling_analyst_prompt_asks_for_takeaway(factory):
    llm = RecordingToolLLM()
    factory(llm)(_tool_state())
    assert "**Takeaway**:" in llm.system_message_text()


@pytest.mark.unit
@pytest.mark.parametrize(
    "factory",
    [create_market_analyst, create_news_analyst, create_fundamentals_analyst],
)
def test_tool_calling_analyst_system_message_is_plain_string(factory):
    """The system_message must render as a plain string, not a Python
    tuple-repr. A stray trailing comma in the concatenation makes
    system_message a 1-tuple, which the template substitutes as
    ``('...',)`` — corrupting the prompt while still containing every
    expected substring."""
    llm = RecordingToolLLM()
    factory(llm)(_tool_state())
    text = llm.system_message_text()
    assert "',)" not in text and '",)' not in text, "system_message rendered as a tuple-repr"
    assert "\n('" not in text and '\n("' not in text, "system_message rendered as a tuple-repr"


@pytest.mark.unit
def test_sentiment_analyst_prompt_asks_for_takeaway():
    system_message = _build_system_message(
        ticker="AAPL",
        start_date="2026-01-01",
        end_date="2026-01-08",
        news_block="<unavailable>",
        stocktwits_block="<unavailable>",
        reddit_block="<unavailable>",
    )
    assert "**Takeaway**:" in system_message
