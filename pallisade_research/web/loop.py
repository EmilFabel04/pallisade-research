# pallisade_research/web/loop.py
from __future__ import annotations

from dataclasses import dataclass

from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import (
    CAP_ESTIMATES, CAP_NEWS, CAP_RESEARCH, CAP_TRANSCRIPTS,
)
from pallisade_research.web.fetch import fetch_url as _fetch_url
from pallisade_research.web.search import web_search as _web_search

_WEB_CAPS = (CAP_NEWS, CAP_RESEARCH, CAP_ESTIMATES, CAP_TRANSCRIPTS)
_BUDGETS = {"shallow": (1, 3), "deep": (3, 8)}

_SYSTEM = (
    "You research the open web to answer the analyst's question and fill the "
    "listed coverage gaps. Call web_search, then fetch_url on the most relevant "
    "results. You GATHER SOURCES ONLY — you must not state facts, write prose, or "
    "answer the question yourself. Stop calling tools once you have enough."
)

_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for pages relevant to the question.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Fetch a URL from a prior search result and extract its readable text.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]


@dataclass(frozen=True)
class WebResearchResult:
    records: tuple[Record, ...]
    used: bool
    unavailable: bool


def _capability_for(query: ResearchQuery) -> str:
    for cap in query.capabilities:
        if cap in _WEB_CAPS:
            return cap
    return CAP_RESEARCH


def research(
    query: ResearchQuery,
    *,
    sdk,
    model: str,
    depth: str = "shallow",
    search=_web_search,
    fetch=_fetch_url,
) -> WebResearchResult:
    max_rounds, max_fetches = _BUDGETS.get(depth, _BUDGETS["shallow"])
    records: list[Record] = []
    searches = 0
    fetches = 0

    try:
        cap = _capability_for(query)
        max_iters = 2 * (max_rounds + max_fetches)

        convo = [{
            "role": "user",
            "content": (
                f"Question: {query.question}\n"
                f"Ticker: {query.ticker or '(none)'}\n"
                "Research the web and gather sources; do not answer."
            ),
        }]

        for _ in range(max_iters):
            msg = sdk.messages.create(
                model=model, max_tokens=1024, system=_SYSTEM, tools=_TOOLS, messages=convo,
            )
            tool_uses = [b for b in msg.content if getattr(b, "type", "") == "tool_use"]
            if not tool_uses:
                break
            convo.append({"role": "assistant", "content": _assistant_blocks(tool_uses)})
            results = []
            for tu in tool_uses:
                out = "done"
                if tu.name == "web_search" and searches < max_rounds:
                    searches += 1
                    hits = search(tu.input.get("query", ""))
                    out = "\n".join(f"{h.title} | {h.url}" for h in hits) or "no results"
                elif tu.name == "fetch_url" and fetches < max_fetches:
                    fetches += 1
                    doc = fetch(tu.input.get("url", ""))
                    if doc is not None:
                        for passage in doc.passages:
                            records.append(Record(
                                id=f"web-{len(records)}",
                                capability=cap,
                                key=f"web.{len(records)}",
                                value=passage,
                                provenance=Provenance(
                                    source="web", locator=doc.url, as_of=doc.published,
                                    detail=doc.title, tier=3, liveness="live",
                                ),
                            ))
                    out = "fetched"
                else:
                    out = "budget exhausted; stop calling tools"
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
            convo.append({"role": "user", "content": results})
            if searches >= max_rounds and fetches >= max_fetches:
                break
    except Exception:  # noqa: BLE001 — never break the turn
        return WebResearchResult(records=tuple(records), used=bool(records), unavailable=True)

    return WebResearchResult(records=tuple(records), used=bool(records), unavailable=False)


def _assistant_blocks(tool_uses) -> list[dict]:
    return [
        {"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input}
        for tu in tool_uses
    ]
