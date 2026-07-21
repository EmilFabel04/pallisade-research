from __future__ import annotations

from typing import Callable

from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_FUNDAMENTALS


def _default_fetcher(ticker: str) -> dict:
    import yfinance as yf

    info = yf.Ticker(ticker).info or {}
    keys = ("marketCap", "trailingPE", "totalRevenue", "profitMargins")
    return {k: info[k] for k in keys if k in info}


class YFinanceSource:
    """Free fundamentals fallback. `fetcher` is injectable for deterministic tests."""

    source = "yfinance"
    tier = 3
    capabilities = frozenset({CAP_FUNDAMENTALS})

    def __init__(self, fetcher: Callable[[str], dict] | None = None):
        self._fetcher = fetcher or _default_fetcher

    def fetch(self, query: ResearchQuery) -> list[Record]:
        if query.ticker is None:
            return []
        data = self._fetcher(query.ticker)
        out: list[Record] = []
        for key, value in data.items():
            out.append(
                Record(
                    id=f"yfinance-{query.ticker}-{key}",
                    capability=CAP_FUNDAMENTALS,
                    key=f"fundamentals.{key}",
                    value=value,
                    provenance=Provenance(
                        source="yfinance",
                        locator=f"https://finance.yahoo.com/quote/{query.ticker}",
                        as_of=None,
                        detail=f"yfinance {key}",
                    ),
                )
            )
        return out
