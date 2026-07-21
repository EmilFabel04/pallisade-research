"""Moneyweb RSS news fetcher for South African market coverage.

Moneyweb (https://www.moneyweb.co.za) is the dominant SA business news site
for JSE-listed companies. It exposes a public RSS feed at ``/feed/`` that
returns recent articles across all sections. The feed does not support
per-ticker filtering, so we fetch the recent batch and filter client-side
by ticker root or company-name tokens.

Why this matters: yfinance/Alpha Vantage news coverage on pure-JSE tickers
is thin or zero (e.g. Capitec returned 0 yfinance news items in the
2026-05-26 smoke test). Moneyweb fills that gap with the SA-specific
institutional framing the asset manager actually reads daily.

No API key required.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tradingagents.dataflows._symbol_filter import (
    company_tokens,
    resolve_company_name,
    symbol_root,
)

logger = logging.getLogger(__name__)

# Multiplex across section feeds — each returns the ~10 most recent items
# in that section, and dedupe by link. Empirically (2026-05-26) the four
# below combine to ~40 unique articles per fetch, which is enough to give
# a useful per-ticker hit rate without scraping.
_FEED_URLS = (
    "https://www.moneyweb.co.za/feed/",
    "https://www.moneyweb.co.za/category/companies-and-deals/feed/",
    "https://www.moneyweb.co.za/category/markets/feed/",
    "https://www.moneyweb.co.za/category/investing/feed/",
)
_UA = "tradingagents/0.2 (+https://github.com/TauricResearch/TradingAgents)"

# Strip HTML tags from RSS description fields without pulling in a parser.
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return _TAG_RE.sub("", s or "").strip()


def _parse_pubdate(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def _fetch_one_feed(url: str, timeout: float) -> list[dict]:
    """Fetch a single Moneyweb RSS URL. Empty list on any failure."""
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/rss+xml"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("Moneyweb feed fetch failed for %s: %s", url, exc)
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        logger.warning("Moneyweb feed parse failed for %s: %s", url, exc)
        return []
    items = []
    for item in root.iter("item"):
        items.append(
            {
                "title": (item.findtext("title") or "").strip(),
                "description": _strip_html(item.findtext("description") or ""),
                "link": (item.findtext("link") or "").strip(),
                "pub_date": _parse_pubdate(item.findtext("pubDate")),
                "categories": [
                    c.text.strip() for c in item.findall("category") if c.text
                ],
            }
        )
    return items


def _fetch_feed(timeout: float = 10.0) -> list[dict]:
    """Fetch and dedupe Moneyweb articles across the configured section feeds.

    Each section feed returns the ~10 most recent items for that section;
    we union and dedupe by ``link`` to maximise per-ticker hit rate without
    extra scraping.
    """
    seen_links: set[str] = set()
    combined: list[dict] = []
    for url in _FEED_URLS:
        for art in _fetch_one_feed(url, timeout):
            link = art.get("link") or art.get("title", "")
            if link in seen_links:
                continue
            seen_links.add(link)
            combined.append(art)
    # Sort newest-first so the per-ticker filter walks recent articles first.
    combined.sort(
        key=lambda a: a.get("pub_date") or datetime(1970, 1, 1, tzinfo=timezone.utc),
        reverse=True,
    )
    return combined


def _article_mentions(article: dict, symbol: str, company_name: str | None) -> bool:
    """Match if symbol or any company-token (or full company name) appears
    in the title or description.

    Symbol-only match is allowed even for ambiguous symbols here because
    Moneyweb's editorial context (SA business news) is already a strong
    contextual filter — far less collision risk than open-internet Reddit.
    """
    text = ((article.get("title") or "") + " " + (article.get("description") or "")).lower()
    if not text:
        return False
    sym = symbol.lower()
    # Symbol mention: require word boundary so "AGL" doesn't match "anglo-gold"
    # only by substring (we want exact symbol references like "AGL" or "AGL:JO").
    if re.search(rf"\b{re.escape(sym)}\b", text):
        return True
    tokens = company_tokens(company_name)
    if any(tok in text for tok in tokens):
        return True
    # Full multi-word company name (lowercase) as a fallback — handles
    # "Anglo American" being mentioned without either token-only match.
    if company_name and company_name.lower() in text:
        return True
    return False


def fetch_moneyweb_articles(
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    company_name: str | None = None,
) -> str:
    """Return a formatted news block for the given ticker from Moneyweb.

    Filters by company-name tokens and ticker root. Respects an optional
    date window (inclusive). Returns a placeholder string when no articles
    match, so the caller never has to handle exceptions.
    """
    sym = symbol_root(ticker)
    if company_name is None:
        company_name = resolve_company_name(ticker)

    articles = _fetch_feed()
    if not articles:
        return f"<Moneyweb feed unavailable for {sym}>"

    start_dt = (
        datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if start_date else None
    )
    end_dt = (
        datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date else None
    )

    matched: list[dict] = []
    for art in articles:
        if not _article_mentions(art, sym, company_name):
            continue
        pub = art.get("pub_date")
        if start_dt and pub and pub < start_dt:
            continue
        if end_dt and pub and pub > end_dt:
            continue
        matched.append(art)
        if len(matched) >= limit:
            break

    if not matched:
        return f"<no Moneyweb articles mentioning {sym} ({company_name or 'company'}) in recent feed>"

    lines = [f"## Moneyweb articles for {sym}" + (f" ({company_name})" if company_name else "")]
    for art in matched:
        pub_str = art["pub_date"].strftime("%Y-%m-%d") if art.get("pub_date") else "?"
        cats = f" [{', '.join(art['categories'])}]" if art.get("categories") else ""
        lines.append(f"\n### [{pub_str}]{cats} {art['title']} (source: Moneyweb)")
        if art.get("description"):
            desc = art["description"]
            if len(desc) > 400:
                desc = desc[:400] + "…"
            lines.append(desc)
        if art.get("link"):
            lines.append(f"Link: {art['link']}")

    return "\n".join(lines)
