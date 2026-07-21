# tests/test_risk_debators_voice.py
from types import SimpleNamespace

import pytest

from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
from tradingagents.agents.risk_mgmt.conservative_debator import create_conservative_debator
from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator


class RecordingLLM:
    def __init__(self):
        self.prompt = None

    def invoke(self, prompt):
        self.prompt = prompt
        return SimpleNamespace(content="argument")


def _state():
    return {
        "market_report": "m", "sentiment_report": "s",
        "news_report": "n", "fundamentals_report": "f",
        "investment_plan": "**Recommendation**: Buy\n**Thesis**: ...",
        "trader_investment_plan": "**Most Likely Failure Cause**: ...",
        "risk_debate_state": {
            "history": "", "aggressive_history": "", "conservative_history": "",
            "neutral_history": "", "current_aggressive_response": "",
            "current_conservative_response": "", "current_neutral_response": "",
            "count": 0,
        },
    }


@pytest.mark.unit
@pytest.mark.parametrize("factory", [
    create_aggressive_debator, create_conservative_debator, create_neutral_debator,
])
def test_risk_prompt_references_view_and_premortem_in_house_style(factory):
    llm = RecordingLLM()
    factory(llm)(_state())
    p = llm.prompt.lower()
    assert "investment view" in p
    assert "pre-mortem" in p
    assert "institutional research analyst" in p
    # Old retail framing gone.
    assert "compelling case for the trader's decision" not in p
    assert "conversationally" not in p
