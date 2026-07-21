"""Conversational brain for the Research Copilot.

Adds true multi-turn behaviour on top of the deterministic engine:

  1. an LLM resolves the latest user turn *in conversation context* into a
     standalone research query (so "what about its margins?" knows what "its"
     refers to) — this is the LLM implementation of the planner seam;
  2. the deterministic engine fetches + reconciles + grounds the answer;
  3. an LLM narrates ONLY the grounded, cited findings (no new facts).

Every numeric fact the user sees still comes from the grounded `CitedAnswer`
(the artifact); the narration is a framing summary constrained to those
findings. If no LLM is available the whole thing degrades to the deterministic
single-turn planner with a templated narration — it never hard-fails.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pallisade_research.citations import tiered_sources_line
from pallisade_research.engine import gather_structured, ground
from pallisade_research.models import CitedAnswer, ResearchQuery
from pallisade_research.planner import plan as deterministic_plan
from pallisade_research.sources.base import (
    ALL_CAPABILITIES,
    CAP_FUNDAMENTALS,
)
from pallisade_research.sources.registry import ClientConfig
from pallisade_research.sources.base import ResearchSource
from pallisade_research.web.loop import research as web_research

PLAN_TOOL = {
    "name": "plan_research",
    "description": (
        "Resolve the user's latest message, in the context of the conversation "
        "so far, into a standalone research query."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": ["string", "null"],
                "description": (
                    "The EXCHANGE-QUALIFIED ticker (e.g. AAPL for US, NPN.JO / SBK.JO for "
                    "Johannesburg, 0700.HK for Hong Kong, 7203.T for Tokyo). ALWAYS include "
                    "the exchange suffix for non-US listings; US tickers take no suffix. "
                    "Null if no single equity is implied."
                ),
            },
            "standalone_question": {
                "type": "string",
                "description": "The user's question rewritten to stand alone without the prior conversation.",
            },
            "capabilities": {
                "type": "array",
                "items": {"type": "string", "enum": sorted(ALL_CAPABILITIES)},
                "description": "Which data capabilities to retrieve for this question.",
            },
            "entity": {
                "type": ["string", "null"],
                "description": (
                    "Non-ticker subject: a country (for macro), an FX pair (e.g. 'USD/ZAR'), "
                    "a crypto ('bitcoin'), or an index ('S&P 500'). Null for listed equities."
                ),
            },
            "entity_type": {
                "type": ["string", "null"],
                "enum": ["country", "fx", "crypto", "index", "commodity", None],
                "description": "The kind of `entity`. Null when a ticker is used instead.",
            },
        },
        "required": ["ticker", "standalone_question", "capabilities"],
    },
}

_PLAN_SYSTEM = (
    "You are the query planner for an equity research tool. Given the running "
    "conversation, resolve the latest user message into one standalone research "
    "query: identify the ticker in question (carrying it over from earlier turns "
    "when the user says 'it'/'its'/'they'), ALWAYS exchange-qualifying it for "
    "non-US listings (Standard Bank -> SBK.JO, Naspers -> NPN.JO, Tencent -> "
    "0700.HK, Toyota -> 7203.T; US names take no suffix), rewrite the question to stand alone, "
    "and choose the data capabilities to pull. Use 'fundamentals' for valuation/"
    "financials and 'holdings' to surface the client's own position. Request "
    "'news'/'research'/'transcripts'/'estimates' ONLY when the question is "
    "specifically about recent developments, headlines, sentiment, or 'what's "
    "happening' — do NOT request them for valuation, fundamentals, price, or "
    "market-structure questions. For broad 'is it worth holding' conviction "
    "questions, request all capabilities. For a COUNTRY's economy use capability "
    "'macro' with entity=<country> and entity_type='country'. For FX pairs, crypto, "
    "or indices use 'markets' with entity=<pair/coin/index> and the matching "
    "entity_type ('fx'/'crypto'/'index'). Leave ticker null when using entity. "
    "For a stock's current price or recent market movement ('how is it doing', "
    "'market shifts', 'price'), ALSO request 'markets' — it works with the equity ticker."
)

# holdings is intentionally NOT a default: it is only requested when the
# planner detects the user is asking about their own position, otherwise it
# manufactures a permanent "no coverage for 'holdings'" gap on every query.
# fundamentals only — news/research are pulled only when the question is about
# developments (see planner prompt), so a plain overview no longer drags in a
# wall of off-topic headlines.
_DEFAULT_CAPS = (CAP_FUNDAMENTALS,)


def _plan_with_llm(sdk: Any, model: str, history: list[dict], message: str) -> ResearchQuery:
    convo = [{"role": m["role"], "content": str(m["content"])} for m in history]
    convo.append({"role": "user", "content": message})
    msg = sdk.messages.create(
        model=model,
        max_tokens=512,
        system=[{"type": "text", "text": _PLAN_SYSTEM}],
        tools=[PLAN_TOOL],
        tool_choice={"type": "tool", "name": "plan_research"},
        messages=convo,
    )
    payload = next((b.input for b in msg.content if getattr(b, "type", "") == "tool_use"), None)
    if payload is None:
        raise ValueError("planner did not return plan_research tool call")
    ticker = payload.get("ticker")
    ticker = ticker.upper() if isinstance(ticker, str) and ticker.strip() else None
    caps = tuple(payload.get("capabilities") or _DEFAULT_CAPS)
    entity = payload.get("entity")
    entity = entity.strip() if isinstance(entity, str) and entity.strip() else None
    entity_type = payload.get("entity_type") or None
    return ResearchQuery(
        question=payload.get("standalone_question") or message,
        ticker=ticker,
        capabilities=caps,
        entity=entity,
        entity_type=entity_type,
    )


def _narrate_with_llm(sdk: Any, model: str, answer: CitedAnswer) -> str:
    findings = "\n".join(f"- {c.text}" for c in answer.claims) or "(none returned)"
    gaps = "; ".join(g.note for g in answer.gaps) or "none"
    unavailable = ", ".join(answer.sources_unavailable) or "none"
    prompt = (
        f'Question: "{answer.question}"\n\n'
        f"GROUNDED FINDINGS — these are the ONLY facts you may state:\n{findings}\n\n"
        f"Coverage gaps: {gaps}\nUnavailable sources: {unavailable}\n\n"
        "Write a 2–3 sentence answer for a professional analyst. Use ONLY the "
        "findings above and keep the source attribution shown in brackets. "
        "Only mention a coverage gap if it is directly relevant to what the user "
        "asked — do NOT volunteer unrelated gaps. Never invent a number.\n\n"
        "FORMAT: Respond in plain prose only. Do NOT use Markdown — no headers "
        "(#), no blockquotes (>), no bullet or numbered lists, no bold (**), no "
        "backticks. Just sentences."
    )
    msg = sdk.messages.create(
        model=model,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def _template_narration(answer: CitedAnswer) -> str:
    n = len(answer.claims)
    used = tiered_sources_line(answer, today=date.today()) or "no sources"
    if n == 0:
        return "No grounded findings — none of the connected sources returned data for this query."
    head = f"{n} cited finding{'s' if n != 1 else ''} drawn from {used}."
    if answer.gaps:
        head += f" Not covered: {answer.gaps[0].note}"
    return head


def converse(
    history: list[dict],
    message: str,
    *,
    config: ClientConfig,
    registry: dict[str, ResearchSource],
    known_tickers: frozenset[str],
    sdk: Any | None = None,
    plan_model: str,
    narrate_model: str,
    depth: str = "shallow",
    web_enabled: bool = False,
    web_model: str | None = None,
) -> dict:
    """Run one conversational turn. Returns {assistant, query, answer}.

    `answer` is a CitedAnswer. Degrades to the deterministic planner + templated
    narration if the LLM is unavailable or errors.
    """
    # 1. plan (LLM in context, deterministic fallback)
    query: ResearchQuery
    if sdk is not None:
        try:
            query = _plan_with_llm(sdk, plan_model, history, message)
        except Exception:
            query = deterministic_plan(message, known_tickers)
    else:
        query = deterministic_plan(message, known_tickers)

    # 2a. structured retrieval (deterministic — the facts)
    records, used, unavailable = gather_structured(query, config, registry)

    # 2b. autonomous web-research loop (only Records escape it)
    if sdk is not None and web_enabled:
        try:
            web = web_research(query, sdk=sdk, model=web_model or narrate_model, depth=depth)
            records.extend(web.records)
            if web.used:
                used.append("web")
            if web.unavailable:
                unavailable.append("web")
        except Exception:
            unavailable.append("web")

    # 2c. ground everything through one path
    answer = ground(records, query, used=used, unavailable=unavailable)

    # 3. narrate (LLM constrained to findings, templated fallback)
    if sdk is not None:
        try:
            assistant = _narrate_with_llm(sdk, narrate_model, answer)
        except Exception:
            assistant = _template_narration(answer)
    else:
        assistant = _template_narration(answer)

    return {"assistant": assistant, "query": query, "answer": answer}
