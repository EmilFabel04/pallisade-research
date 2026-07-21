from __future__ import annotations

import json
import os
import re
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_MARKETS
from pallisade_research.sources.eodhd import to_eodhd_symbol

_RT = "https://eodhd.com/api/real-time"
_EOD = "https://eodhd.com/api/eod"

_CRYPTO = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP",
           "cardano": "ADA", "dogecoin": "DOGE"}
_INDEX = {"s&p 500": "GSPC", "s&p500": "GSPC", "sp500": "GSPC", "nasdaq": "IXIC",
          "dow jones": "DJI", "dow": "DJI", "ftse 100": "FTSE", "ftse": "FTSE",
          "nikkei": "N225", "jse all share": "JALSH"}


def to_market_symbol(entity: str, entity_type: str) -> str | None:
    if not entity:
        return None
    key = entity.strip().lower()
    if entity_type == "fx":
        pair = re.sub(r"[^A-Za-z]", "", entity).upper()
        return f"{pair}.FOREX" if len(pair) == 6 else None
    if entity_type == "crypto":
        code = _CRYPTO.get(key) or (entity.strip().upper() if entity.isalpha() and len(entity) <= 5 else None)
        return f"{code}-USD.CC" if code else None
    if entity_type == "index":
        code = _INDEX.get(key)
        return f"{code}.INDX" if code else None
    return None  # commodity + unknown: parked


def _default_get(url: str, params: dict):
    req = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "pallisade-research/1.0"})
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8", "replace"))


class EODHDMarketsSource:
    """FX / crypto / index quotes via EODHD real-time (shared platform key)."""

    source = "eodhd_markets"
    tier = 3
    capabilities = frozenset({CAP_MARKETS})

    def __init__(self, http_get: Callable[[str, dict], object] | None = None, api_key: str | None = None):
        self._get = http_get or _default_get
        self._api_key = os.environ.get("EODHD_API_KEY", "") if api_key is None else api_key

    def fetch(self, query: ResearchQuery) -> list[Record]:
        if not self._api_key:
            return []
        # Non-equity: FX / crypto / index keyed by entity.
        if query.entity and query.entity_type:
            return self._entity_quote(query)
        # Equity price / recent market movement, keyed by ticker.
        if query.ticker:
            return self._equity_price(query.ticker)
        return []

    def _entity_quote(self, query: ResearchQuery) -> list[Record]:
        symbol = to_market_symbol(query.entity, query.entity_type)
        if symbol is None:
            return []
        data = self._get(f"{_RT}/{symbol}", {"api_token": self._api_key, "fmt": "json"})
        if not isinstance(data, dict):
            return []
        close = data.get("close")
        if close in (None, "NA"):
            return []
        return [Record(
            id=f"eodhd_markets-{symbol}",
            capability=CAP_MARKETS,
            key=f"markets.{query.entity_type}.{query.entity}",
            value=close,
            provenance=Provenance(
                source="eodhd_markets",
                locator=f"{_RT}/{symbol}",
                as_of=None,
                detail=f"EODHD real-time {symbol}",
            ),
        )]

    def _equity_price(self, ticker: str) -> list[Record]:
        symbol = to_eodhd_symbol(ticker)
        if symbol is None:
            return []
        bars = self._get(f"{_EOD}/{symbol}", {"api_token": self._api_key, "fmt": "json",
                                              "period": "d", "order": "d"})
        if not isinstance(bars, list) or not bars:
            return []
        latest = bars[0]
        close = latest.get("close")
        if close in (None, "NA"):
            return []
        prov = Provenance(source="eodhd_markets", locator=f"{_EOD}/{symbol}", as_of=None,
                          detail=f"EODHD EOD {symbol} ({latest.get('date')})")
        out = [Record(id=f"eodhd_markets-{symbol}-price", capability=CAP_MARKETS,
                      key="markets.price", value=close, provenance=prov)]
        if len(bars) > 1:
            prev = bars[1].get("close")
            if isinstance(prev, (int, float)) and prev:
                change = round((close - prev) / prev * 100, 2)
                out.append(Record(id=f"eodhd_markets-{symbol}-change", capability=CAP_MARKETS,
                                  key="markets.change_pct", value=change, provenance=prov))
        return out
