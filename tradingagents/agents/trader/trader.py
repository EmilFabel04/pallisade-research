# Modified for Pallisade Research by Emil Fabel, 2026. Original: TradingAgents (Apache-2.0).
"""Pre-mortem: adversarially stress-tests the Research Manager's investment view.

Formerly the Trader (execution desk). Execution and sizing are the human PM's
job, so this node no longer issues a trade — it runs a pre-mortem on the RM's
recommendation. Output is stored under ``trader_investment_plan`` for graph and
state continuity, and is read by the risk committee and the Portfolio Manager.
The ``create_trader`` factory name is kept so graph wiring is untouched.
"""

from __future__ import annotations

import functools

from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import PreMortem, render_pre_mortem
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_house_style_instruction,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_trader(llm):
    structured_llm = bind_structured(llm, PreMortem, "Pre-Mortem")

    def trader_node(state, name):
        company_name = state["company_of_interest"]
        asset_type = state.get("asset_type", "stock")
        instrument_context = build_instrument_context(company_name, asset_type)
        investment_plan = state["investment_plan"]

        prompt = (
            f"You are running a PRE-MORTEM on the Research Manager's investment "
            f"view for {company_name}. {instrument_context}\n\n"
            f"Assume the recommendation below proves wrong over its horizon. Work "
            f"backward: name the single most likely cause of failure, the most "
            f"fragile assumption the thesis depends on, and the material risk the "
            f"bull/bear debate under-weighted. Do not issue a trade, a price, or a "
            f"position size.\n\n"
            f"Research Manager's investment view:\n{investment_plan}"
            + get_house_style_instruction()
            + get_language_instruction()
        )

        pre_mortem = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_pre_mortem,
            "Pre-Mortem",
        )

        return {
            "messages": [AIMessage(content=pre_mortem)],
            "trader_investment_plan": pre_mortem,
            "sender": name,
        }

    return functools.partial(trader_node, name="Pre-Mortem")
