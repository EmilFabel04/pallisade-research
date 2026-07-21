from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Callable
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

_SNIPPET_LEN = 280
_MAX_PASSAGES = 12
_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class FetchedDoc:
    url: str
    title: str
    published: date | None
    passages: tuple[str, ...]


def _default_get(url: str) -> str:
    req = Request(url, headers={"User-Agent": "pallisade-research/1.0"})
    with urlopen(req, timeout=20) as resp:  # noqa: S310 (user-provided URL, best-effort fetch)
        return resp.read().decode("utf-8", "replace")


def _find_published(soup: BeautifulSoup) -> date | None:
    # Try meta first
    meta = soup.find("meta", attrs={"property": "article:published_time"})
    raw = meta.get("content") if meta and meta.get("content") else None
    if raw:
        m = _ISO.search(raw)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                pass

    # Fall back to <time> if meta didn't yield an ISO date
    t = soup.find("time")
    raw = t.get("datetime") if t and t.get("datetime") else None
    if raw:
        m = _ISO.search(raw)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                pass

    return None


def fetch_url(url: str, *, http_get: Callable[[str], str] | None = None) -> FetchedDoc:
    get = http_get or _default_get
    try:
        html = get(url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        published = _find_published(soup)
        seen: set[str] = set()
        passages: list[str] = []
        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)[:_SNIPPET_LEN]
            if not text or text in seen:
                continue
            seen.add(text)
            passages.append(text)
            if len(passages) >= _MAX_PASSAGES:
                break
        return FetchedDoc(url=url, title=title, published=published, passages=tuple(passages))
    except Exception:  # noqa: BLE001 — a bad page must not break the loop
        return FetchedDoc(url=url, title="", published=None, passages=())
