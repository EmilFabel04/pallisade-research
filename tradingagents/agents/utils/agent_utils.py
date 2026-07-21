from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news
)


def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Applied to every agent whose output reaches the saved report —
    analysts, researchers, debaters, research manager, trader, and
    portfolio manager — so a non-English run produces a fully localized
    report rather than a mix of languages.
    """
    from tradingagents.dataflows.config import get_config
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def build_instrument_context(ticker: str, asset_type: str = "stock") -> str:
    """Describe the exact instrument so agents preserve exchange-qualified tickers."""
    instrument_label = "asset" if asset_type == "crypto" else "instrument"
    extra_hint = (
        " Treat it as a crypto asset rather than a company, and do not assume company fundamentals are available."
        if asset_type == "crypto"
        else ""
    )
    return (
        f"The {instrument_label} to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`, `-USD`)."
        + extra_hint
    )


def get_house_style_instruction() -> str:
    """Shared institutional-voice + anti-hallucination suffix for every agent prompt.

    Appended (alongside get_language_instruction) by the researchers, research
    manager, pre-mortem, risk debaters, and portfolio manager so the whole
    graph reads as an analyst team rather than a retail signals service, and
    never fabricates a figure the provided reports do not support.
    """
    return (
        "\n\n---\n"
        "House style — follow exactly:\n"
        "- Write as an institutional research analyst: measured, precise, "
        "probabilistic, risk-first. No emojis, no salutations ('ladies and "
        "gentlemen'), no hype, no exclamation marks.\n"
        "- Ground every claim in the provided reports. Do not invent figures, "
        "prices, or facts; if the data does not support a point, say so rather "
        "than fill the gap.\n"
        "- Give no trade-execution or portfolio-construction instructions: no "
        "entry price, no stop-loss, no order mechanics, and no position size "
        "or share count. The reader owns sizing and execution."
    )

def get_takeaway_instruction() -> str:
    """One-line directive making a free-text agent lead with a skim takeaway.

    Applied to the free-text agents (bull/bear researchers and the four
    analysts) so their reports open with a scannable bottom line, matching
    the structured agents' `**Takeaway**:` line.
    """
    return (
        "\n\nBegin your response with a single line "
        "`**Takeaway**: <one sentence>` distilling your bottom line, "
        "then continue with the full analysis."
    )


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        
