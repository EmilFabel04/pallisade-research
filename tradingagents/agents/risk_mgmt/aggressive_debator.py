from tradingagents.agents.utils.agent_utils import (
    get_house_style_instruction,
    get_language_instruction,
)


def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")

        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_view = state["investment_plan"]
        pre_mortem = state["trader_investment_plan"]

        prompt = f"""As the Aggressive Risk Analyst on the investment committee, argue the higher-conviction, higher-return reading of the case. Weigh the Research Manager's investment view against the pre-mortem and the conservative and neutral analysts, and make the evidence-based case that the upside is under-priced relative to the risks — without dismissing the risks.

Research Manager's investment view:
{investment_view}

Pre-mortem (red-team on the view):
{pre_mortem}

Respond directly to the conservative and neutral analysts' points with data. Reports for reference:
Market Research: {market_research_report}
Social Sentiment: {sentiment_report}
World Affairs: {news_report}
Fundamentals: {fundamentals_report}
Conversation so far: {history}
Last conservative argument: {current_conservative_response}
Last neutral argument: {current_neutral_response}
If the others have not spoken yet, state your own reading from the reports.""" + get_house_style_instruction() + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"Aggressive Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return aggressive_node
