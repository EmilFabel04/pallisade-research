# Modified for Pallisade Research by Emil Fabel, 2026. Original: TradingAgents (Apache-2.0).
"""Pydantic schemas used by agents that produce structured output.

The framework's primary artifact is still prose: each agent's natural-language
reasoning is what users read in the saved markdown reports and what the
downstream agents read as context.  Structured output is layered onto the
three decision-making agents (Research Manager, Trader, Portfolio Manager)
so that:

- Their outputs follow consistent section headers across runs and providers
- Each provider's native structured-output mode is used (json_schema for
  OpenAI/xAI, response_schema for Gemini, tool-use for Anthropic)
- Schema field descriptions become the model's output instructions, freeing
  the prompt body to focus on context and the rating-scale guidance
- A render helper turns the parsed Pydantic instance back into the same
  markdown shape the rest of the system already consumes, so display,
  memory log, and saved reports keep working unchanged
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared rating types
# ---------------------------------------------------------------------------


class PortfolioRating(str, Enum):
    """5-tier rating used by the Research Manager and Portfolio Manager."""

    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"


class Conviction(str, Enum):
    """Confidence tier attached to a rating."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# ---------------------------------------------------------------------------
# Research Manager
# ---------------------------------------------------------------------------


class ResearchPlan(BaseModel):
    """The Research Manager's investment view — pre-risk-committee.

    Captures which side of the bull/bear debate carried the argument and the
    decision-ready view that follows from it. It states a valuation *view*,
    never an order or a position size.
    """

    recommendation: PortfolioRating = Field(
        description=(
            "The investment recommendation. Exactly one of Buy / Overweight / "
            "Hold / Underweight / Sell. Reserve Hold for genuinely balanced "
            "evidence; otherwise commit to the stronger side."
        ),
    )
    conviction: Conviction = Field(
        description=(
            "Confidence in the recommendation: Low / Medium / High, reflecting "
            "how decisively the debate favoured one side."
        ),
    )
    takeaway: str = Field(
        description=(
            "A single-sentence distillation of this section's bottom line, "
            "for a skim view."
        ),
    )
    thesis: str = Field(
        description=(
            "The core investment thesis: which arguments carried and why, "
            "anchored in the reports. Do not invent figures."
        ),
    )
    fair_value: Optional[str] = Field(
        default=None,
        description=(
            "A valuation view derived from the thesis, e.g. 'fair value ~$230, "
            "~13% upside over 12 months'. A view, never an entry level or order. "
            "Omit if the data does not support one."
        ),
    )
    time_horizon: Optional[str] = Field(
        default=None,
        description="Horizon for the thesis to play out, e.g. '6-12 months'.",
    )
    catalysts: str = Field(
        description=(
            "Specific events that could move the thesis (earnings, launches, "
            "regulation), with rough timing where known."
        ),
    )
    key_risks: str = Field(
        description="The main risks to the thesis, drawn from the bear case and reports.",
    )
    falsifiers: str = Field(
        description=(
            "What observable evidence would prove the thesis wrong and warrant "
            "re-underwriting the view."
        ),
    )


def render_research_plan(plan: ResearchPlan) -> str:
    """Render a ResearchPlan to markdown. First line is the takeaway."""
    parts = [
        f"**Takeaway**: {plan.takeaway}",
        "",
        f"**Recommendation**: {plan.recommendation.value}",
        "",
        f"**Conviction**: {plan.conviction.value}",
        "",
        f"**Thesis**: {plan.thesis}",
    ]
    if plan.fair_value:
        parts += ["", f"**Fair Value**: {plan.fair_value}"]
    if plan.time_horizon:
        parts += ["", f"**Time Horizon**: {plan.time_horizon}"]
    parts += [
        "",
        f"**Catalysts**: {plan.catalysts}",
        "",
        f"**Key Risks**: {plan.key_risks}",
        "",
        f"**Falsifiers**: {plan.falsifiers}",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Trader (pre-mortem)
# ---------------------------------------------------------------------------


class PreMortem(BaseModel):
    """Adversarial pre-mortem on the Research Manager's investment view.

    Formerly the Trader. Assumes the recommendation is wrong and works
    backward: the most likely cause of failure, the most fragile assumption,
    and what the bull/bear debate under-weighted. It issues no trade, price,
    or position size — execution and sizing belong to the human PM.
    """

    takeaway: str = Field(
        description=(
            "A single-sentence distillation of this section's bottom line, "
            "for a skim view."
        ),
    )
    most_likely_failure_cause: str = Field(
        description=(
            "Assume the recommendation proves wrong over its horizon. State the "
            "single most likely cause, grounded in the reports and the debate."
        ),
    )
    weakest_link: str = Field(
        description=(
            "The most fragile assumption the thesis depends on — the one whose "
            "failure would do the most damage."
        ),
    )
    underweighted_by_debate: str = Field(
        description=(
            "A material risk or consideration the bull/bear debate glossed over "
            "or under-weighted."
        ),
    )


def render_pre_mortem(pm: PreMortem) -> str:
    """Render a PreMortem to markdown. No trade action or execution levels."""
    return "\n".join([
        f"**Takeaway**: {pm.takeaway}",
        "",
        f"**Most Likely Failure Cause**: {pm.most_likely_failure_cause}",
        "",
        f"**Weakest Link**: {pm.weakest_link}",
        "",
        f"**Under-weighted by the Debate**: {pm.underweighted_by_debate}",
    ])


# ---------------------------------------------------------------------------
# Portfolio Manager
# ---------------------------------------------------------------------------


class PortfolioDecision(BaseModel):
    """The Portfolio Manager's final, risk-adjusted research verdict.

    Delivered after the risk committee. States whether the committee confirmed
    or moved the Research Manager's view, and what the human PM must weigh
    before sizing. It issues no size, entry, stop, or order.
    """

    rating: PortfolioRating = Field(
        description=(
            "The final position rating after the risk debate. Exactly one of "
            "Buy / Overweight / Hold / Underweight / Sell."
        ),
    )
    conviction: Conviction = Field(
        description="Confidence in the final rating: Low / Medium / High.",
    )
    takeaway: str = Field(
        description=(
            "A single-sentence distillation of this section's bottom line, "
            "for a skim view."
        ),
    )
    executive_summary: str = Field(
        description=(
            "The risk-adjusted call in two to four sentences: the rating, and "
            "whether the risk committee confirmed or moved the Research "
            "Manager's view. No entry, sizing, or order mechanics."
        ),
    )
    investment_thesis: str = Field(
        description=(
            "Detailed reasoning anchored in specific evidence from the debate. "
            "Incorporate any prior lessons referenced in the prompt context; "
            "otherwise rely solely on the current analysis."
        ),
    )
    what_to_weigh: str = Field(
        description=(
            "The considerations the human portfolio manager must own before "
            "sizing: liquidity, existing exposure, mandate fit, correlation. "
            "Frame as what to consider — never a number or a position size."
        ),
    )
    fair_value: Optional[str] = Field(
        default=None,
        description=(
            "A valuation view derived from the thesis (a view, never an entry "
            "level). Omit if unsupported."
        ),
    )
    time_horizon: Optional[str] = Field(
        default=None,
        description="Recommended holding period, e.g. '3-6 months'.",
    )


def render_pm_decision(decision: PortfolioDecision) -> str:
    """Render to the markdown shape downstream expects; **Rating** stays first."""
    parts = [
        f"**Rating**: {decision.rating.value}",
        "",
        f"**Takeaway**: {decision.takeaway}",
        "",
        f"**Conviction**: {decision.conviction.value}",
        "",
        f"**Executive Summary**: {decision.executive_summary}",
        "",
        f"**Investment Thesis**: {decision.investment_thesis}",
        "",
        f"**What to Weigh**: {decision.what_to_weigh}",
    ]
    if decision.fair_value:
        parts += ["", f"**Fair Value**: {decision.fair_value}"]
    if decision.time_horizon:
        parts += ["", f"**Time Horizon**: {decision.time_horizon}"]
    return "\n".join(parts)
