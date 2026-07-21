from unittest.mock import MagicMock

import pytest

from tradingagents.agents.managers.portfolio_manager import create_portfolio_manager
from tradingagents.agents.schemas import Conviction, PortfolioDecision, PortfolioRating


def _pm_state():
    return {
        "company_of_interest": "NVDA",
        "investment_plan": "**Recommendation**: Buy\n**Thesis**: ...",
        "trader_investment_plan": "**Most Likely Failure Cause**: demand normalises",
        "risk_debate_state": {
            "history": "risk debate...", "aggressive_history": "", "conservative_history": "",
            "neutral_history": "", "current_aggressive_response": "",
            "current_conservative_response": "", "current_neutral_response": "", "count": 3,
        },
    }


@pytest.mark.unit
def test_pm_prompt_is_house_style_and_references_pre_mortem():
    captured = {}
    decision = PortfolioDecision(
        rating=PortfolioRating.OVERWEIGHT, conviction=Conviction.MEDIUM,
        takeaway="t",
        executive_summary="s", investment_thesis="t", what_to_weigh="w",
    )
    structured = MagicMock()
    structured.invoke.side_effect = lambda prompt: captured.__setitem__("p", prompt) or decision
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    result = create_portfolio_manager(llm)(_pm_state())
    p = captured["p"].lower()
    assert "institutional research analyst" in p
    assert "pre-mortem" in p
    # The reframe: the old trade-ticket label is gone. A substring check for
    # "position siz" can't distinguish "give a position size" (bad) from "do
    # not give a position size" (fine — that's the PM's own correct framing
    # instruction), so it isn't a meaningful prompt-level check here; the
    # no-sizing property is already enforced structurally and tested at the
    # schema/render level in Task 4 instead. This phrase, by contrast, does
    # not appear anywhere in the shared house-style suffix, so its absence
    # precisely verifies the reframe with no collision risk.
    assert "trader's transaction proposal" not in p
    assert result["final_trade_decision"].splitlines()[0] == "**Rating**: Overweight"
