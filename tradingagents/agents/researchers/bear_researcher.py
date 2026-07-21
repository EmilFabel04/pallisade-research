from tradingagents.agents.utils.agent_utils import (
    get_house_style_instruction,
    get_language_instruction,
    get_takeaway_instruction,
)


def _bear_prompt(*, opening, target_label, fundamentals_label, market_research_report,
                 sentiment_report, news_report, fundamentals_report, history, current_response):
    resources = f"""Resources available:

Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
{fundamentals_label}: {fundamentals_report}
Conversation history of the debate: {history}"""

    suffix = get_takeaway_instruction() + get_house_style_instruction() + get_language_instruction()

    if opening:
        return f"""You are a Bear Analyst delivering the OPENING argument against a position in the {target_label}. No bull analyst has spoken yet, so present your own independent, evidence-based case — do not reference, pre-empt, or invent an opposing bull argument.

Build the case on:
- Risks: saturation, financial fragility, or macro threats, cited from the reports.
- Competitive weakness: soft positioning, fading innovation, competitor threats.
- Evidence: financial data, trends, or adverse developments, each tied to a source.

{resources}
Open with a self-contained bear case grounded in the evidence, so the bull has a concrete case to answer.""" + suffix

    return f"""You are a Bear Analyst arguing against a position in the {target_label}. Build an evidence-based case on risks, competitive weakness, and the data — and answer the bull's argument directly on the merits.

Address:
- Risks: saturation, financial fragility, macro threats.
- Competitive weakness: positioning, innovation, competitor threats.
- Evidence: financial data, trends, adverse developments — each cited.
- The bull's case: engage its specific points with data; expose over-optimistic assumptions, and concede where it has a fair point.

{resources}
Last bull argument: {current_response}
Respond on the evidence; do not simply list facts.""" + suffix


def create_bear_researcher(llm):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")
        bull_history = investment_debate_state.get("bull_history", "")
        current_response = investment_debate_state.get("current_response", "")
        asset_type = state.get("asset_type", "stock")
        target_label = "stock" if asset_type == "stock" else "asset"
        fundamentals_label = (
            "Company fundamentals report"
            if asset_type == "stock"
            else "Asset fundamentals report (may be unavailable for crypto)"
        )

        # Symmetric with the bull: only frame the turn as a rebuttal once the
        # opposing side has actually spoken. The bear normally follows the bull,
        # so this is almost always a rebuttal — the guard just keeps it honest if
        # the flow ever changes.
        opening = not bull_history.strip()

        prompt = _bear_prompt(
            opening=opening,
            target_label=target_label,
            fundamentals_label=fundamentals_label,
            market_research_report=state["market_report"],
            sentiment_report=state["sentiment_report"],
            news_report=state["news_report"],
            fundamentals_report=state["fundamentals_report"],
            history=history,
            current_response=current_response,
        )

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
