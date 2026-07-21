"""Tests for structured-output agents (Trader and Research Manager).

The Portfolio Manager has its own coverage in tests/test_memory_log.py
(which exercises the full memory-log → PM injection cycle).  This file
covers the parallel schemas, render functions, and graceful-fallback
behavior we added for the Trader and Research Manager so all three
decision-making agents share the same shape.
"""

from unittest.mock import MagicMock

import pytest

from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.schemas import (
    Conviction,
    PortfolioDecision,
    PortfolioRating,
    PreMortem,
    ResearchPlan,
    render_pm_decision,
    render_pre_mortem,
    render_research_plan,
)
from tradingagents.agents.trader.trader import create_trader
from tradingagents.agents.utils.rating import parse_rating


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderPreMortem:
    def test_renders_all_fields_and_no_trade_ticket(self):
        pm = PreMortem(
            takeaway="The thesis breaks if data-centre demand softens.",
            most_likely_failure_cause="Data-center demand normalises faster than priced.",
            weakest_link="The thesis assumes hyperscaler capex stays above trend.",
            underweighted_by_debate="Customer concentration risk was barely discussed.",
        )
        md = render_pre_mortem(pm)
        assert "**Most Likely Failure Cause**: Data-center demand" in md
        assert "**Weakest Link**: The thesis assumes" in md
        assert "**Under-weighted by the Debate**: Customer concentration" in md
        # Execution vocabulary must be gone entirely.
        assert "FINAL TRANSACTION PROPOSAL" not in md
        assert "Action" not in md
        assert "Entry" not in md
        assert "Stop" not in md


@pytest.mark.unit
class TestRenderResearchPlan:
    def _plan(self, rating=PortfolioRating.OVERWEIGHT):
        return ResearchPlan(
            recommendation=rating,
            conviction=Conviction.MEDIUM,
            takeaway="Overweight on a durable services-mix thesis.",
            thesis="Bull case carried; AI tailwind intact.",
            fair_value="fair value ~$230, ~13% upside over 12 months",
            time_horizon="6-12 months",
            catalysts="Next earnings (Aug); data-center refresh (Q4).",
            key_risks="Multiple compression; export-control headlines.",
            falsifiers="Two quarters of decelerating data-center revenue.",
        )

    def test_required_and_optional_fields_render(self):
        md = render_research_plan(self._plan())
        assert md.splitlines()[0].startswith("**Takeaway**:")
        assert "**Recommendation**: Overweight" in md
        assert "**Conviction**: Medium" in md
        assert "**Thesis**: Bull case carried" in md
        assert "**Fair Value**: fair value ~$230" in md
        assert "**Time Horizon**: 6-12 months" in md
        assert "**Catalysts**: Next earnings" in md
        assert "**Key Risks**: Multiple compression" in md
        assert "**Falsifiers**: Two quarters" in md
        # No execution language leaks in.
        assert "Strategic Actions" not in md
        assert "position siz" not in md.lower()

    def test_optional_fields_omitted_when_absent(self):
        p = ResearchPlan(
            recommendation=PortfolioRating.HOLD,
            conviction=Conviction.LOW,
            takeaway="Balanced; no edge either way.",
            thesis="Balanced.",
            catalysts="None near-term.",
            key_risks="Macro.",
            falsifiers="Guidance cut.",
        )
        md = render_research_plan(p)
        assert "Fair Value" not in md
        assert "Time Horizon" not in md

    def test_all_5_tier_ratings_render(self):
        for rating in PortfolioRating:
            md = render_research_plan(self._plan(rating))
            assert f"**Recommendation**: {rating.value}" in md


@pytest.mark.unit
class TestRenderPortfolioDecision:
    def test_rating_header_first_and_no_execution(self):
        d = PortfolioDecision(
            rating=PortfolioRating.UNDERWEIGHT,
            conviction=Conviction.MEDIUM,
            takeaway="Risk committee tempered the RM's view on margin risk.",
            executive_summary="Risk committee tempered the RM's Hold to Underweight on margin risk.",
            investment_thesis="Bear case on gross margin is under-appreciated by the bulls.",
            what_to_weigh="Existing sector exposure, liquidity at size, and mandate fit before sizing.",
            fair_value="fair value ~$180, ~8% downside",
            time_horizon="3-6 months",
        )
        md = render_pm_decision(d)
        # parse_rating relies on this being the first line.
        assert md.splitlines()[0] == "**Rating**: Underweight"
        assert "**Conviction**: Medium" in md
        assert "**Executive Summary**: Risk committee" in md
        assert "**Investment Thesis**: Bear case" in md
        assert "**What to Weigh**: Existing sector exposure" in md
        assert "**Fair Value**: fair value ~$180" in md
        assert "**Time Horizon**: 3-6 months" in md
        assert "position siz" not in md.lower()
        assert "stop" not in md.lower()

    def test_parse_rating_still_reads_header(self):
        from tradingagents.agents.utils.rating import parse_rating
        d = PortfolioDecision(
            rating=PortfolioRating.BUY,
            conviction=Conviction.HIGH,
            takeaway="t",
            executive_summary="s", investment_thesis="t", what_to_weigh="w",
        )
        assert parse_rating(render_pm_decision(d)) == "Buy"


def test_research_plan_render_takeaway_is_line_1():
    plan = TestRenderResearchPlan()._plan()  # existing helper; will gain takeaway kwarg in step 3
    md = render_research_plan(plan)
    assert md.splitlines()[0].startswith("**Takeaway**:")
    assert "**Recommendation**: Overweight" in md


def test_pre_mortem_render_takeaway_is_line_1():
    pm = PreMortem(
        takeaway="The thesis breaks if data-centre demand softens.",
        most_likely_failure_cause="Demand normalises faster than priced.",
        weakest_link="Sustained hyperscaler capex.",
        underweighted_by_debate="Customer concentration.",
    )
    md = render_pre_mortem(pm)
    assert md.splitlines()[0].startswith("**Takeaway**:")
    assert "**Most Likely Failure Cause**:" in md


def test_pm_render_rating_line_1_takeaway_second_field():
    d = PortfolioDecision(
        rating=PortfolioRating.BUY,
        conviction=Conviction.HIGH,
        takeaway="Risk committee confirmed the constructive view.",
        executive_summary="Buy, high conviction.",
        investment_thesis="Grounded in the reports.",
        what_to_weigh="Liquidity and existing exposure.",
    )
    md = render_pm_decision(d)
    lines = md.splitlines()
    assert lines[0] == "**Rating**: Buy"
    assert "**Takeaway**: Risk committee confirmed the constructive view." in md
    assert md.index("**Takeaway**:") < md.index("**Conviction**:")
    assert parse_rating(md) == "Buy"


# ---------------------------------------------------------------------------
# Trader agent: structured happy path + fallback
# ---------------------------------------------------------------------------


def _make_trader_state():
    return {
        "company_of_interest": "NVDA",
        "asset_type": "stock",
        "investment_plan": "**Recommendation**: Buy\n**Conviction**: High\n**Thesis**: ...",
    }


def _structured_premortem_llm(captured: dict, pm: PreMortem | None = None):
    if pm is None:
        pm = PreMortem(
            takeaway="Demand normalisation is the key risk to the thesis.",
            most_likely_failure_cause="Demand normalises faster than priced.",
            weakest_link="Assumes hyperscaler capex stays above trend.",
            underweighted_by_debate="Customer concentration was barely discussed.",
        )
    structured = MagicMock()
    structured.invoke.side_effect = lambda prompt: (
        captured.__setitem__("prompt", prompt) or pm
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm


@pytest.mark.unit
class TestPreMortemAgent:
    def test_structured_path_produces_pre_mortem_markdown(self):
        captured = {}
        trader = create_trader(_structured_premortem_llm(captured))
        result = trader(_make_trader_state())
        plan = result["trader_investment_plan"]
        assert "**Most Likely Failure Cause**:" in plan
        assert "**Weakest Link**:" in plan
        assert "FINAL TRANSACTION PROPOSAL" not in plan
        assert plan in result["messages"][0].content

    def test_prompt_is_a_pre_mortem_over_the_view(self):
        captured = {}
        create_trader(_structured_premortem_llm(captured))(_make_trader_state())
        p = captured["prompt"].lower()
        assert "pre-mortem" in p
        assert "institutional research analyst" in p  # house style present

    def test_falls_back_to_freetext_when_structured_unavailable(self):
        plain = "**Most Likely Failure Cause**: ...\n\n**Weakest Link**: ...\n\n**Under-weighted by the Debate**: ..."
        llm = MagicMock()
        llm.with_structured_output.side_effect = NotImplementedError("provider unsupported")
        llm.invoke.return_value = MagicMock(content=plain)
        result = create_trader(llm)(_make_trader_state())
        assert result["trader_investment_plan"] == plain


# ---------------------------------------------------------------------------
# Research Manager agent: structured happy path + fallback
# ---------------------------------------------------------------------------


def _make_rm_state():
    return {
        "company_of_interest": "NVDA",
        "investment_debate_state": {
            "history": "Bull and bear arguments here.",
            "bull_history": "Bull says...",
            "bear_history": "Bear says...",
            "current_response": "",
            "judge_decision": "",
            "count": 1,
        },
    }


def _structured_rm_llm(captured: dict, plan: ResearchPlan | None = None):
    if plan is None:
        plan = ResearchPlan(
            recommendation=PortfolioRating.HOLD,
            conviction=Conviction.LOW,
            takeaway="Balanced; no edge either way.",
            thesis="Balanced view across both sides.",
            catalysts="None near-term.",
            key_risks="Macro softening.",
            falsifiers="A guidance cut next quarter.",
        )
    structured = MagicMock()
    structured.invoke.side_effect = lambda prompt: (
        captured.__setitem__("prompt", prompt) or plan
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm


@pytest.mark.unit
class TestResearchManagerAgent:
    def test_structured_path_produces_rendered_markdown(self):
        captured = {}
        plan = ResearchPlan(
            recommendation=PortfolioRating.OVERWEIGHT,
            conviction=Conviction.HIGH,
            takeaway="Bull case carries; AI tailwind intact.",
            thesis="Bull case is stronger; AI tailwind intact.",
            catalysts="Next earnings (Aug); data-center refresh (Q4).",
            key_risks="Multiple compression; export-control headlines.",
            falsifiers="Two quarters of decelerating data-center revenue.",
        )
        llm = _structured_rm_llm(captured, plan)
        rm = create_research_manager(llm)
        result = rm(_make_rm_state())
        ip = result["investment_plan"]
        assert "**Recommendation**: Overweight" in ip
        assert "**Conviction**:" in ip
        assert "**Falsifiers**:" in ip

    def test_prompt_uses_5_tier_rating_scale(self):
        """The RM prompt must list all five tiers so the schema enum matches user expectations."""
        captured = {}
        llm = _structured_rm_llm(captured)
        rm = create_research_manager(llm)
        rm(_make_rm_state())
        prompt = captured["prompt"]
        for tier in ("Buy", "Overweight", "Hold", "Underweight", "Sell"):
            assert f"**{tier}**" in prompt, f"missing {tier} in prompt"

    def test_falls_back_to_freetext_when_structured_unavailable(self):
        plain_response = "**Recommendation**: Sell\n\n**Rationale**: ...\n\n**Strategic Actions**: ..."
        llm = MagicMock()
        llm.with_structured_output.side_effect = NotImplementedError("provider unsupported")
        llm.invoke.return_value = MagicMock(content=plain_response)
        rm = create_research_manager(llm)
        result = rm(_make_rm_state())
        assert result["investment_plan"] == plain_response

    def test_prompt_carries_house_style(self):
        captured = {}
        llm = _structured_rm_llm(captured)
        create_research_manager(llm)(_make_rm_state())
        assert "institutional research analyst" in captured["prompt"].lower()
