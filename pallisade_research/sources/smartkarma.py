from __future__ import annotations

import json
from datetime import date
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_RESEARCH

_BASE = "https://api.smartkarma.com/smartwealth/v1/insights"


def _default_get(url: str, params: dict) -> dict:
    req = Request(f"{url}?{urlencode(params)}")
    with urlopen(req, timeout=15) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode("utf-8"))


class SmartkarmaSource:
    """Smartkarma SmartWealth research insights. `http_get` injectable for tests."""

    source = "smartkarma"
    tier = 2
    capabilities = frozenset({CAP_RESEARCH})

    def __init__(self, http_get: Callable[[str, dict], dict] | None = None, api_key: str = ""):
        self._get = http_get or _default_get
        self._api_key = api_key

    def fetch(self, query: ResearchQuery) -> list[Record]:
        if query.ticker is None:
            return []
        payload = self._get(_BASE, {"symbol": query.ticker, "api_key": self._api_key})
        out: list[Record] = []
        for ins in payload.get("insights", []):
            out.append(
                Record(
                    id=f"smartkarma-{ins['id']}",
                    capability=CAP_RESEARCH,
                    key=f"research.{ins['id']}",
                    value=ins["title"],
                    provenance=Provenance(
                        source="smartkarma",
                        locator=ins["url"],
                        as_of=date.fromisoformat(ins["published"]),
                        detail="Smartkarma insight",
                    ),
                )
            )
        return out
