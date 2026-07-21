from tradingagents.agents.utils.agent_utils import (
    get_house_style_instruction,
    get_language_instruction,
)


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_view = state["investment_plan"]
        pre_mortem = state["trader_investment_plan"]

        prompt = f"""As the Neutral Risk Analyst on the investment committee, arbitrate between the aggressive and conservative readings. Weigh the Research Manager's investment view against the pre-mortem and both sides, and give the balanced, evidence-based assessment of where the reward genuinely justifies the risk and where it does not.

Research Manager's investment view:
{investment_view}

Pre-mortem (red-team on the view):
{pre_mortem}

Engage both the aggressive and conservative analysts' points with data. Reports for reference:
Market Research: {market_research_report}
Social Sentiment: {sentiment_report}
World Affairs: {news_report}
Fundamentals: {fundamentals_report}
Conversation so far: {history}
Last aggressive argument: {current_aggressive_response}
Last conservative argument: {current_conservative_response}
If the others have not spoken yet, state your own reading from the reports.""" + get_house_style_instruction() + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"Neutral Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_aggressive_response": risk_debate_state.get(
                "current_aggressive_response", ""
            ),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
