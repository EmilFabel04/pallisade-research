from types import SimpleNamespace

import pytest

from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
from tradingagents.agents.utils.agent_utils import (
    get_house_style_instruction,
    get_takeaway_instruction,
)


class RecordingLLM:
    def __init__(self):
        self.prompt = None

    def invoke(self, prompt):
        self.prompt = prompt
        return SimpleNamespace(content="argument body")


def _state(bull_hist="", bear_hist=""):
    return {
        "investment_debate_state": {
            "history": "", "bull_history": bull_hist, "bear_history": bear_hist,
            "current_response": "", "count": 0,
        },
        "market_report": "m", "sentiment_report": "s",
        "news_report": "n", "fundamentals_report": "f",
        "asset_type": "stock",
    }


RETAIL = ("compelling", "conversational", "ladies and gentlemen", "🐂", "📈", "dynamic debate")


@pytest.mark.unit
@pytest.mark.parametrize("factory", [create_bull_researcher, create_bear_researcher])
def test_prompt_has_house_style_and_no_retail(factory):
    llm = RecordingLLM()
    factory(llm)(_state())
    prompt = llm.prompt
    p = prompt.lower()
    assert "institutional research analyst" in p
    assert "no position size" in p or "position size" in p
    # Retail-absence targets the researcher's OWN prompt text, not the shared
    # house-style suffix (which legitimately names 'ladies and gentlemen' as a
    # banned salutation). Strip the shared suffix before checking.
    body = prompt.replace(get_house_style_instruction(), "").lower()
    for word in RETAIL:
        assert word.lower() not in body, f"retail phrase leaked: {word}"


@pytest.mark.unit
def test_bull_opens_when_no_bear_yet():
    llm = RecordingLLM()
    create_bull_researcher(llm)(_state(bear_hist=""))
    assert "OPENING" in llm.prompt


@pytest.mark.unit
def test_bull_rebuts_once_bear_has_spoken():
    llm = RecordingLLM()
    create_bull_researcher(llm)(_state(bear_hist="Bear Analyst: risks..."))
    assert "OPENING" not in llm.prompt


@pytest.mark.unit
def test_takeaway_instruction_content_is_retail_safe():
    t = get_takeaway_instruction()
    assert "**Takeaway**:" in t
    low = t.lower()
    for word in ("compelling", "conversational", "ladies and gentlemen", "dynamic debate"):
        assert word not in low


@pytest.mark.unit
def test_bull_prompt_asks_for_takeaway():
    llm = RecordingLLM()
    create_bull_researcher(llm)(_state())
    assert "**Takeaway**:" in llm.prompt


@pytest.mark.unit
def test_bear_prompt_asks_for_takeaway():
    llm = RecordingLLM()
    create_bear_researcher(llm)(_state())
    assert "**Takeaway**:" in llm.prompt
