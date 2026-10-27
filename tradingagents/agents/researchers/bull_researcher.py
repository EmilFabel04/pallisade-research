# Modified for Pallisade Research by Emil Fabel, 2026. Original: TradingAgents (Apache-2.0).
from tradingagents.agents.utils.agent_utils import (
    get_house_style_instruction,
    get_language_instruction,
    get_takeaway_instruction,
)


def _bull_prompt(*, opening, target_label, fundamentals_label, market_research_report,
                 sentiment_report, news_report, fundamentals_report, history, current_response):
    resources = f"""Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
{fundamentals_label}: {fundamentals_report}
Conversation history of the debate: {history}"""

    suffix = get_takeaway_instruction() + get_house_style_instruction() + get_language_instruction()

    if opening:
        return f"""You are a Bull Analyst delivering the OPENING argument for a position in the {target_label}. No bear analyst has spoken yet, so present your own independent, evidence-based thesis — do not reference, pre-empt, or invent an opposing bear argument.

Build the case on:
- Growth: market opportunity, revenue trajectory, and scalability, cited from the reports.
- Competitive position: durable advantages — products, franchise, share.
- Evidence: financial health, industry trends, and recent developments, each tied to a source.

{resources}
Open with a self-contained bull thesis grounded in the evidence, so the bear has a concrete case to answer.""" + suffix

    return f"""You are a Bull Analyst arguing for a position in the {target_label}. Build an evidence-based case on growth, competitive position, and the financial and industry data — and answer the bear's argument directly on the merits.

Address:
- Growth: market opportunity, revenue trajectory, and scalability.
- Competitive position: durable advantages.
- Evidence: financial health, industry trends, recent developments — each cited.
- The bear's case: engage its specific points with data; show where its assumptions are too pessimistic, and concede where it has a fair point.

{resources}
Last bear argument: {current_response}
Respond on the evidence; do not simply list data.""" + suffix


def create_bull_researcher(llm):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")
        bear_history = investment_debate_state.get("bear_history", "")
        current_response = investment_debate_state.get("current_response", "")
        asset_type = state.get("asset_type", "stock")
        target_label = "stock" if asset_type == "stock" else "asset"
        fundamentals_label = (
            "Company fundamentals report"
            if asset_type == "stock"
            else "Asset fundamentals report (may be unavailable for crypto)"
        )

        # The bull opens the debate, so on its first turn no bear has spoken.
        # Framing that turn as a rebuttal makes the model invent a phantom bear
        # to counter ("here's what the bears want you to forget..."), which reads
        # as staged. Only ask for a rebuttal once the bear has actually argued.
        opening = not bear_history.strip()

        prompt = _bull_prompt(
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

        argument = f"Bull Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
