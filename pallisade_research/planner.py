from __future__ import annotations

import re

from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import (
    ALL_CAPABILITIES,
    CAP_FUNDAMENTALS,
    CAP_METRICS,
    CAP_NEWS,
    CAP_RESEARCH,
)

_CONVICTION = ("hold", "invest", "worth", "buy", "sell")
_TREND = ("grow", "growth", "trend", "cagr", "over time", "history", "historical", "vs average")


def plan(question: str, known_tickers: frozenset[str]) -> ResearchQuery:
    """Plan a research query by extracting ticker and selecting capabilities.

    Extracts the first recognized ticker from the question. Selects base capabilities
    based on keyword heuristics (conviction keywords → all; "news" → news+research;
    default → fundamentals only).

    Holdings is NOT auto-added: it is only requested via the conviction branch
    (an "is it worth holding" question already pulls all capabilities). Forcing
    it onto every ticker query manufactures a permanent "no coverage for
    'holdings'" gap when no position source is connected.

    Args:
        question: The user's research question.
        known_tickers: Frozenset of recognized ticker symbols (uppercase).

    Returns:
        ResearchQuery with extracted ticker, capabilities, and question text.
    """
    ticker = None
    for raw in re.split(r"\s+", question):
        token = raw.strip("?.,!").upper()
        if token in known_tickers:
            ticker = token
            break

    low = question.lower()
    if any(w in low for w in _CONVICTION):
        caps = tuple(sorted(ALL_CAPABILITIES))
    elif "news" in low:
        caps = (CAP_NEWS, CAP_RESEARCH)
    else:
        # A plain question gets fundamentals only — news/research are scoped to
        # questions that explicitly ask about developments (the "news" branch),
        # so ordinary overviews no longer pull a wall of off-topic articles.
        caps = (CAP_FUNDAMENTALS,)

    if any(w in low for w in _TREND):
        caps = tuple(sorted(set(caps) | {CAP_METRICS}))

    return ResearchQuery(question=question, ticker=ticker, capabilities=caps)
