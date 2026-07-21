from __future__ import annotations

from typing import Protocol, runtime_checkable

from pallisade_research.models import Record, ResearchQuery

CAP_FUNDAMENTALS = "fundamentals"
CAP_ESTIMATES = "estimates"
CAP_NEWS = "news"
CAP_TRANSCRIPTS = "transcripts"
CAP_RESEARCH = "research"
CAP_HOLDINGS = "holdings"
CAP_MACRO = "macro"
CAP_MARKETS = "markets"

ALL_CAPABILITIES = frozenset({
    CAP_FUNDAMENTALS, CAP_ESTIMATES, CAP_NEWS,
    CAP_TRANSCRIPTS, CAP_RESEARCH, CAP_HOLDINGS,
    CAP_MACRO, CAP_MARKETS,
})


@runtime_checkable
class ResearchSource(Protocol):
    source: str
    capabilities: frozenset[str]

    def fetch(self, query: ResearchQuery) -> list[Record]: ...
