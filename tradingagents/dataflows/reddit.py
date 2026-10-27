# Modified for Pallisade Research by Emil Fabel, 2026. Original: TradingAgents (Apache-2.0).
"""Reddit search fetcher for ticker-specific discussion posts.

Uses Reddit's public JSON endpoints (``reddit.com/r/{sub}/search.json``)
which do not require an API key. Public throughput is ~10 requests per
minute per IP, well within budget for a single agent run that queries
a handful of finance subreddits per ticker.

Returns formatted plaintext blocks ready for prompt injection. Degrades
gracefully — returns a placeholder string rather than raising, so callers
never have to special-case missing data.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tradingagents.dataflows._symbol_filter import (
    post_is_relevant,
    symbol_root,
)

logger = logging.getLogger(__name__)

_API = "https://www.reddit.com/r/{sub}/search.json?{qs}"
_UA = "tradingagents/0.2 (+https://github.com/TauricResearch/TradingAgents)"

# Default subreddits ordered roughly by signal density for ticker-specific
# discussion. wallstreetbets has the most volume but most noise; stocks /
# investing trend more measured. Caller can override.
DEFAULT_SUBREDDITS = ("wallstreetbets", "stocks", "investing")

# JSE / South African coverage: r/wallstreetbets etc. return ~0 signal on
# JSE names. These subreddits actually discuss them.
JSE_SUBREDDITS = ("JSE", "PersonalFinanceZA", "southafrica")


def _default_subreddits_for(ticker: str) -> tuple[str, ...]:
    """Pick subreddits based on the exchange suffix. ``.JO`` -> SA set."""
    if ticker and ticker.upper().endswith(".JO"):
        return JSE_SUBREDDITS
    return DEFAULT_SUBREDDITS


def _fetch_subreddit(
    ticker: str,
    sub: str,
    limit: int,
    timeout: float,
) -> list[dict]:
    qs = urlencode({
        "q": ticker,
        "restrict_sr": "on",
        "sort": "new",
        "t": "week",  # last 7 days
        "limit": limit,
    })
    url = _API.format(sub=sub, qs=qs)
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except (HTTPError, URLError, json.JSONDecodeError, TimeoutError) as exc:
        logger.warning("Reddit fetch failed for r/%s · %s: %s", sub, ticker, exc)
        return []
    children = (payload.get("data") or {}).get("children") or []
    return [c.get("data", {}) for c in children if isinstance(c, dict)]


def fetch_reddit_posts(
    ticker: str,
    subreddits: Iterable[str] | None = None,
    limit_per_sub: int = 5,
    timeout: float = 10.0,
    inter_request_delay: float = 0.4,
    company_name: str | None = None,
) -> str:
    """Fetch recent Reddit posts mentioning ``ticker`` across finance
    subreddits and return them as a formatted plaintext block.

    ``inter_request_delay`` keeps us under Reddit's public rate limit
    (~10 req/min per IP) even if the caller queries many subreddits.

    ``ticker`` may include an exchange suffix (e.g. ``NPN.JO``); the suffix
    is stripped for the Reddit search query but used to pick SA-flavoured
    default subreddits.

    Short or English-word symbols (e.g. ``F``, ``T``, ``GM``, ``CPI``) are
    filtered post-fetch via :func:`_symbol_filter.post_is_relevant` to
    avoid false-positive matches; pass ``company_name`` to enable
    company-token disambiguation on top of cashtag matching.
    """
    if subreddits is None:
        subreddits = _default_subreddits_for(ticker)

    search_symbol = symbol_root(ticker)
    blocks = []
    total_posts = 0
    total_filtered = 0
    for i, sub in enumerate(subreddits):
        if i > 0:
            time.sleep(inter_request_delay)
        posts = _fetch_subreddit(search_symbol, sub, limit_per_sub, timeout)

        # Disambiguation filter — drop posts whose text doesn't contain a
        # cashtag or company-name token when the symbol is ambiguous.
        kept = []
        for p in posts:
            blob = (p.get("title") or "") + " \n " + (p.get("selftext") or "")
            if post_is_relevant(search_symbol, company_name, blob):
                kept.append(p)
        total_filtered += len(posts) - len(kept)
        total_posts += len(kept)

        if not kept:
            blocks.append(
                f"r/{sub}: <no posts found mentioning {search_symbol} in the past 7 days>"
            )
            continue

        lines = [f"r/{sub} — {len(kept)} recent posts mentioning {search_symbol}:"]
        for p in kept:
            title = (p.get("title") or "").replace("\n", " ").strip()
            score = p.get("score", 0)
            comments = p.get("num_comments", 0)
            created = p.get("created_utc")
            created_str = (
                time.strftime("%Y-%m-%d", time.gmtime(created)) if created else "?"
            )
            selftext = (p.get("selftext") or "").replace("\n", " ").strip()
            if len(selftext) > 240:
                selftext = selftext[:240] + "…"
            lines.append(
                f"  [{created_str} · {score:>4}↑ · {comments:>3}c] {title}"
                + (f"\n    body excerpt: {selftext}" if selftext else "")
            )
        blocks.append("\n".join(lines))

    if total_filtered:
        logger.info(
            "Reddit disambiguation filter dropped %d posts for %s",
            total_filtered, search_symbol,
        )

    if total_posts == 0:
        return (
            f"<no Reddit posts found mentioning {search_symbol} across "
            f"{', '.join(f'r/{s}' for s in subreddits)} in the past 7 days>"
        )
    return "\n\n".join(blocks)
