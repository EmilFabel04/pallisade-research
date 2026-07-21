"""Google News RSS fetcher — the universal news floor.

Whatever ticker the agent is asked about, Google News almost always has
recent coverage from somewhere (Moneyweb, BusinessLive, News24, Fin24,
MyBroadband, Reuters, Bloomberg, the local paper). It's region-aware,
free, key-less, and not rate-limited at our request volume.

Used as the breadth net behind yfinance (primary) and Moneyweb
(SA-curated). yfinance is fast and structured; Moneyweb adds SA editorial
voice; Google News makes sure we never come back empty-handed.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from tradingagents.dataflows._symbol_filter import (
    resolve_company_name,
    symbol_root,
)

logger = logging.getLogger(__name__)

_RSS_BASE = "https://news.google.com/rss/search"
_UA = "tradingagents/0.2 (+https://github.com/TauricResearch/TradingAgents)"

# Strip embedded HTML in <description>. Google wraps the title in <a href=...>
# so the description text is mostly noise; we keep the original title field
# and discard description to avoid leaking redirect URLs into the prompt.
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


def _region_for(ticker: str) -> tuple[str, str, str]:
    """Pick the Google News region params from the ticker's exchange suffix.

    Returns ``(hl, gl, ceid)`` tuple suitable for the RSS query string.
    JSE ``.JO`` -> South Africa. EU ``.AS`` -> Netherlands but we keep
    English-language because most JSE-listed dual-stocks publish in English
    SA/UK outlets. Default -> US English.
    """
    t = (ticker or "").upper()
    if t.endswith(".JO"):
        return ("en-ZA", "ZA", "ZA:en")
    if t.endswith(".AS"):
        return ("en", "NL", "NL:en")
    if t.endswith(".L"):
        return ("en-GB", "GB", "GB:en")
    if t.endswith(".AX"):
        return ("en-AU", "AU", "AU:en")
    return ("en-US", "US", "US:en")


def _build_query(symbol: str, company_name: str | None) -> str:
    """Prefer the company name as a quoted phrase (fewer false positives).

    Falls back to the bare symbol if no company name resolved. The symbol
    alone is a weak query for short/ambiguous tickers (F, T, GM, CPI) and
    will be filtered later anyway by ``_symbol_filter.post_is_relevant``
    only if needed — but Google News already does decent disambiguation
    via context, especially with regional restrictions.
    """
    if company_name:
        return f'"{company_name}"'
    return symbol


def _fetch_rss(query: str, region: tuple[str, str, str], timeout: float) -> list[dict]:
    """Fetch one Google News RSS query and parse into article dicts."""
    hl, gl, ceid = region
    qs = f"q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={ceid}"
    url = f"{_RSS_BASE}?{qs}"
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/rss+xml"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("Google News fetch failed (%s): %s", url, exc)
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        logger.warning("Google News parse failed: %s", exc)
        return []

    items = []
    for item in root.iter("item"):
        source = item.find("source")
        items.append(
            {
                "title": _strip_html(item.findtext("title") or ""),
                "link": (item.findtext("link") or "").strip(),
                "pub_date": _parse_pubdate(item.findtext("pubDate")),
                "source": (source.text or "").strip() if source is not None else "Google News",
            }
        )
    return items


def fetch_google_news_articles(
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 15,
    company_name: str | None = None,
) -> str:
    """Return a formatted news block for ``ticker`` from Google News.

    Pulls a region-appropriate RSS feed (SA for ``.JO``, US for default,
    etc.), filters to the date window if provided, and formats up to
    ``limit`` articles.

    Returns a placeholder string on no-results so the caller never has to
    handle exceptions. Falls back to a symbol-only query if company name
    resolution fails.
    """
    sym = symbol_root(ticker)
    if company_name is None:
        company_name = resolve_company_name(ticker)

    region = _region_for(ticker)
    query = _build_query(sym, company_name)
    articles = _fetch_rss(query, region, timeout=10.0)

    # Fallback: if a company-name query returned nothing, retry with the
    # bare symbol. Rare in practice but cheap insurance.
    if not articles and company_name:
        articles = _fetch_rss(sym, region, timeout=10.0)

    if not articles:
        return f"<no Google News results for {sym} ({company_name or 'company'})>"

    # Date-filter and dedupe by title.
    start_dt = (
        datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if start_date else None
    )
    end_dt = (
        datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date else None
    )

    seen_titles: set[str] = set()
    matched: list[dict] = []
    for art in articles:
        title = art.get("title") or ""
        if not title or title in seen_titles:
            continue
        pub = art.get("pub_date")
        if start_dt and pub and pub < start_dt:
            continue
        if end_dt and pub and pub > end_dt:
            continue
        seen_titles.add(title)
        matched.append(art)
        if len(matched) >= limit:
            break

    if not matched:
        return (
            f"<no Google News results for {sym} ({company_name or 'company'}) "
            f"in {start_date} to {end_date}>"
        )

    lines = [
        f"## Google News — {sym}"
        + (f" ({company_name})" if company_name else "")
        + f", region={region[1]}"
    ]
    for art in matched:
        pub_str = art["pub_date"].strftime("%Y-%m-%d") if art.get("pub_date") else "?"
        src = art.get("source") or "Google News"
        lines.append(f"\n### [{pub_str}] {art['title']} (source: {src})")
        if art.get("link"):
            lines.append(f"Link: {art['link']}")

    return "\n".join(lines)
