from __future__ import annotations

import json
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_MACRO

_BASE = "https://api.worldbank.org/v2"
# label -> World Bank indicator code
_INDICATORS = {
    "gdp_usd": "NY.GDP.MKTP.CD",
    "gdp_growth_pct": "NY.GDP.MKTP.KD.ZG",
    "inflation_pct": "FP.CPI.TOTL.ZG",
    "unemployment_pct": "SL.UEM.TOTL.ZS",
}
# name -> ISO2 (majors + African focus). Extend as needed.
_ISO2 = {
    "south africa": "ZA", "nigeria": "NG", "egypt": "EG", "kenya": "KE",
    "ghana": "GH", "morocco": "MA", "ethiopia": "ET", "tanzania": "TZ",
    "united states": "US", "usa": "US", "united kingdom": "GB", "uk": "GB",
    "china": "CN", "japan": "JP", "india": "IN", "germany": "DE", "france": "FR",
    "brazil": "BR", "russia": "RU", "canada": "CA", "australia": "AU",
    "south korea": "KR", "korea": "KR", "mexico": "MX", "indonesia": "ID",
    "saudi arabia": "SA", "turkey": "TR", "netherlands": "NL", "switzerland": "CH",
}
_VALID_CODES = set(_ISO2.values())


def to_iso2(name: str) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    if key in _ISO2:
        return _ISO2[key]
    up = name.strip().upper()
    if len(up) == 2 and up in _VALID_CODES:
        return up
    return None


def _default_get(url: str, params: dict):
    req = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "pallisade-research/1.0"})
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8", "replace"))


class WorldBankSource:
    """Any-country macro indicators via the free World Bank API."""

    source = "worldbank"
    tier = 3
    capabilities = frozenset({CAP_MACRO})

    def __init__(self, http_get: Callable[[str, dict], object] | None = None):
        self._get = http_get or _default_get

    def fetch(self, query: ResearchQuery) -> list[Record]:
        if query.entity_type != "country" or not query.entity:
            return []
        iso2 = to_iso2(query.entity)
        if iso2 is None:
            return []
        out: list[Record] = []
        for label, code in _INDICATORS.items():
            url = f"{_BASE}/country/{iso2}/indicator/{code}"
            try:
                data = self._get(url, {"format": "json", "mrv": 1})
            except Exception:  # noqa: BLE001 — a flaky indicator must not sink the rest
                continue
            if not (isinstance(data, list) and len(data) == 2 and data[1]):
                continue
            row = data[1][0]
            value = row.get("value")
            if value is None:
                continue
            cname = (row.get("country") or {}).get("value", iso2)
            out.append(
                Record(
                    id=f"worldbank-{iso2}-{label}",
                    capability=CAP_MACRO,
                    key=f"macro.{label}",
                    value=value,
                    provenance=Provenance(
                        source="worldbank",
                        locator=f"{url}?mrv=1",
                        as_of=None,
                        detail=f"World Bank {label} for {cname} ({row.get('date')})",
                    ),
                )
            )
        return out
