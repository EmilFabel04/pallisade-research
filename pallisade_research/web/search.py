from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable
from urllib.request import Request, urlopen

_TAVILY = "https://api.tavily.com/search"


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str


def _default_post(url: str, body: dict) -> object:
    req = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "pallisade-research/1.0"},
        method="POST",
    )
    with urlopen(req, timeout=20) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode("utf-8", "replace"))


def web_search(
    query: str,
    *,
    k: int = 5,
    http_post: Callable[[str, dict], object] | None = None,
    api_key: str | None = None,
) -> list[SearchHit]:
    key = os.environ.get("WEB_SEARCH_API_KEY", "") if api_key is None else api_key
    if not key:
        return []
    post = http_post or _default_post
    payload = post(_TAVILY, {"api_key": key, "query": query, "max_results": k})
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return []
    out: list[SearchHit] = []
    for r in payload["results"]:
        if not isinstance(r, dict):
            continue
        out.append(SearchHit(title=r.get("title", ""), url=r.get("url", ""), snippet=r.get("content", "")))
    return out
