"""Live market snapshots for the watchlist.

This module is the single seam between the API and yfinance. It is also the
seam a future data-connections vendor layer would replace: swap
``ticker_factory`` and nothing above this module changes.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from tradingagents.dataflows.stockstats_utils import yf_retry

logger = logging.getLogger(__name__)

MAX_SYMBOLS = 50
SPARK_POINTS = 30

# quote_one runs on a sync route sharing the app's threadpool with every other
# sync endpoint. yf_retry's default budget (3 retries, 2/4/8s backoff) can
# block a single symbol for ~14s per call, and quote_one makes up to two such
# calls — ~28s serially. Interactive callers (add_item's validate-only quote,
# and the batch quotes endpoint, which is already per-symbol fault-tolerant)
# fail fast instead: one retry, ~2s, then give up and surface ok:false.
INTERACTIVE_MAX_RETRIES = 1


def _default_ticker_factory(symbol: str) -> Any:
    import yfinance as yf

    return yf.Ticker(symbol)


def normalize_symbols(raw: str) -> list[str]:
    """Split a comma-separated query param into clean, deduped, capped symbols."""
    out: list[str] = []
    for part in (raw or "").split(","):
        sym = part.strip().upper()
        if sym and sym not in out:
            out.append(sym)
    return out[:MAX_SYMBOLS]


def format_market_cap(value: float | int | None) -> str:
    """Render a raw market cap as a compact display string.

    Always a plain decimal plus a unit suffix, never scientific notation.
    Values are rounded to 3 significant figures; if that rounding pushes the
    scaled value up to 1000 (e.g. 999.6B rounds to "1000B"), it is promoted
    to the next larger unit instead of being displayed as "1000B" or the
    "1e+03B" that `.3g` alone would emit.
    """
    if not value:
        return "—"
    v = float(value)
    units = (("T", 1e12), ("B", 1e9), ("M", 1e6))
    for i, (unit, size) in enumerate(units):
        if v >= size:
            scaled = float(f"{v / size:.3g}")
            if scaled >= 1000 and i > 0:
                unit, size = units[i - 1]
                scaled = float(f"{v / size:.3g}")
            text = f"{scaled:.10f}".rstrip("0").rstrip(".")
            return f"{text}{unit}"
    return f"{v:.0f}"


def downsample_spark(values: list[float], limit: int = SPARK_POINTS) -> list[float]:
    """Reduce a close series to at most ``limit`` points, keeping both endpoints."""
    n = len(values)
    if n <= limit:
        return list(values)
    step = n / limit
    picked = [values[int(i * step)] for i in range(limit)]
    picked[-1] = values[-1]
    return picked


def quote_one(
    symbol: str,
    ticker_factory: Callable[[str], Any] = _default_ticker_factory,
    with_history: bool = True,
) -> dict:
    """Build one live snapshot. Raises LookupError if the symbol has no price.

    ``with_history=False`` skips the spark-line history fetch entirely and
    returns ``spark: []`` — for callers (e.g. add_item's ticker validation)
    that only need price + name and would otherwise pay for a full
    ``period="1mo"`` history call they immediately discard.
    """
    ticker = ticker_factory(symbol)
    info = yf_retry(lambda: ticker.info, max_retries=INTERACTIVE_MAX_RETRIES) or {}

    price = (
        info.get("regularMarketPrice")
        or info.get("currentPrice")
        or info.get("previousClose")
    )
    if price is None:
        raise LookupError(symbol)

    prev = info.get("previousClose")
    change_pct = ((float(price) - float(prev)) / float(prev)) * 100 if prev else 0.0

    spark: list[float] = []
    if with_history:
        try:
            hist = yf_retry(
                lambda: ticker.history(period="1mo"), max_retries=INTERACTIVE_MAX_RETRIES
            )
            closes = [float(c) for c in hist["Close"].tolist()]
            spark = downsample_spark(closes)
        except Exception:  # history is decorative — never fail a quote over it
            logger.warning("spark history unavailable for %s", symbol, exc_info=True)
            spark = []

    return {
        "ticker": symbol,
        "name": info.get("longName") or info.get("shortName") or symbol,
        "price": float(price),
        "changePct": change_pct,
        "marketCap": format_market_cap(info.get("marketCap")),
        "pe": info.get("trailingPE"),
        "spark": spark,
        "ok": True,
    }


def fetch_quotes(
    symbols: list[str],
    ticker_factory: Callable[[str], Any] = _default_ticker_factory,
) -> list[dict]:
    """Quote every symbol. A symbol that fails yields ok:false, never an exception."""
    out: list[dict] = []
    for sym in symbols:
        try:
            out.append(quote_one(sym, ticker_factory=ticker_factory))
        except LookupError:
            out.append({"ticker": sym, "ok": False, "error": "not_found"})
        except Exception:
            logger.warning("quote failed for %s", sym, exc_info=True)
            out.append({"ticker": sym, "ok": False, "error": "fetch_failed"})
    return out
