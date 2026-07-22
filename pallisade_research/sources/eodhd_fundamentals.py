from __future__ import annotations

import json
import os
from datetime import date
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_METRICS
from pallisade_research.sources.eodhd import to_eodhd_symbol

_FUNDAMENTALS = "https://eodhd.com/api/fundamentals"
_MAX_YEARS = 6

# EODHD income-statement field -> our metric name. profit_margin is derived
# per-period from the same row (net_income / revenue), an in-statement ratio.
_INCOME_FIELDS = {"revenue": "totalRevenue", "net_income": "netIncome", "eps": "epsActual"}


def _default_get(url: str, params: dict):
    req = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "pallisade-research/1.0"})
    with urlopen(req, timeout=20) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode("utf-8", "replace"))


def _to_float(raw) -> float | None:
    if raw in (None, "", "NA"):
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _to_date(raw) -> date | None:
    try:
        return date.fromisoformat(str(raw)[:10])
    except (ValueError, TypeError):
        return None


class EODHDFundamentalsSource:
    """Historical fundamentals via EODHD (shared platform key). `http_get` injectable for tests.

    Emits one series-valued Record per metric (revenue, net_income, profit_margin,
    eps), each `evidence_only=True` (inputs, never narrated). A metric with <2
    valid annual points is omitted. Any error -> [] (never hard-fail).
    """

    source = "eodhd_fundamentals"
    tier = 3
    capabilities = frozenset({CAP_METRICS})

    def __init__(self, http_get: Callable[[str, dict], object] | None = None, api_key: str | None = None):
        self._get = http_get or _default_get
        self._api_key = os.environ.get("EODHD_API_KEY", "") if api_key is None else api_key

    def fetch(self, query: ResearchQuery) -> list[Record]:
        if not self._api_key or not query.ticker:
            return []
        symbol = to_eodhd_symbol(query.ticker)
        if symbol is None:
            return []
        try:
            data = self._get(f"{_FUNDAMENTALS}/{symbol}", {"api_token": self._api_key, "fmt": "json"})
        except Exception:  # noqa: BLE001 — never hard-fail
            return []
        if not isinstance(data, dict):
            return []
        try:
            yearly = data.get("Financials", {}).get("Income_Statement", {}).get("yearly", {})
        except AttributeError:
            return []
        if not isinstance(yearly, dict):
            return []

        rows = self._sorted_rows(yearly)
        series = {name: [] for name in ("revenue", "net_income", "profit_margin", "eps")}
        for d, row in rows:
            for name, field in _INCOME_FIELDS.items():
                v = _to_float(row.get(field))
                if v is not None:
                    series[name].append((d, v))
            rev = _to_float(row.get("totalRevenue"))
            ni = _to_float(row.get("netIncome"))
            if rev not in (None, 0) and ni is not None:
                series["profit_margin"].append((d, round(ni / rev * 100, 4)))

        out: list[Record] = []
        for name, points in series.items():
            if len(points) < 2:
                continue
            out.append(self._series_record(symbol, name, tuple(points)))
        return out

    def _sorted_rows(self, yearly: dict) -> list[tuple[date, dict]]:
        rows: list[tuple[date, dict]] = []
        for raw_key, row in yearly.items():
            if not isinstance(row, dict):
                continue
            d = _to_date(row.get("date") or raw_key)
            if d is not None:
                rows.append((d, row))
        rows.sort(key=lambda t: t[0])          # oldest -> newest
        return rows[-_MAX_YEARS:]

    def _series_record(self, symbol: str, name: str, points: tuple) -> Record:
        return Record(
            id=f"eodhd_fundamentals-{symbol}-{name}",
            capability=CAP_METRICS,
            key=f"metrics.{name}.series",
            value=points,
            provenance=Provenance(
                source="eodhd_fundamentals",
                locator=f"{_FUNDAMENTALS}/{symbol}",
                as_of=points[-1][0],
                detail=f"EODHD historical {name} ({symbol})",
            ),
            evidence_only=True,
        )
