from __future__ import annotations

import json
import os
from datetime import date
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_NEWS

_NEWS = "https://eodhd.com/api/news"
_MAXRECORDS = 10

# yfinance-style suffix -> EODHD exchange code. US tickers carry no suffix -> ".US".
_SUFFIX_MAP = {"JO": "JSE", "KS": "KO", "L": "LSE", "HK": "HK", "US": "US"}


def to_eodhd_symbol(ticker: str) -> str | None:
    """Map a yfinance-style ticker to an EODHD symbol, or None if unmapped (parked gap)."""
    if not ticker:
        return None
    if "." not in ticker:
        return f"{ticker}.US"
    base, suffix = ticker.rsplit(".", 1)
    code = _SUFFIX_MAP.get(suffix.upper())
    return f"{base}.{code}" if code else None


def _default_get(url: str, params: dict):
    req = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "pallisade-research/1.0"})
    with urlopen(req, timeout=20) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode("utf-8", "replace"))


def _parse_date(raw: str) -> date | None:
    try:
        return date.fromisoformat(raw[:10])
    except (ValueError, TypeError):
        return None


class EODHDSource:
    """Worldwide news via EODHD (shared platform key). `http_get` injectable for tests."""

    source = "eodhd"
    tier = 3
    capabilities = frozenset({CAP_NEWS})

    def __init__(self, http_get: Callable[[str, dict], object] | None = None, api_key: str | None = None):
        self._get = http_get or _default_get
        self._api_key = os.environ.get("EODHD_API_KEY", "") if api_key is None else api_key

    def fetch(self, query: ResearchQuery) -> list[Record]:
        if not self._api_key or not query.ticker:
            return []
        symbol = to_eodhd_symbol(query.ticker)
        if symbol is None:
            return []
        payload = self._get(_NEWS, {"s": symbol, "api_token": self._api_key, "limit": _MAXRECORDS, "fmt": "json"})
        if not isinstance(payload, list):
            return []
        out: list[Record] = []
        for i, art in enumerate(payload):
            out.append(
                Record(
                    id=f"eodhd-{symbol}-{i}",
                    capability=CAP_NEWS,
                    key=f"news.{i}",
                    value=art.get("title", ""),
                    provenance=Provenance(
                        source="eodhd",
                        locator=art.get("link", ""),
                        as_of=_parse_date(art.get("date", "")),
                        detail="EODHD financial news",
                    ),
                )
            )
        return out
