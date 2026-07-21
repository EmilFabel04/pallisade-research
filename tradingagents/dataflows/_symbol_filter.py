"""Ticker disambiguation helpers used by the social-data fetchers.

Reddit and StockTwits queries on short or English-word symbols (e.g. ``F``
for Ford, ``T`` for AT&T, ``ALL`` for Allstate, ``CPI`` for Capitec) return
posts that mention the *word*, not the company. Without filtering, the
sentiment analyst is fed inflation-discussion as if it were Capitec
sentiment.

This module supplies a small, testable filter:

- ``symbol_root`` strips exchange suffixes (``NPN.JO`` -> ``NPN``).
- ``is_ambiguous`` flags symbols that need disambiguation.
- ``post_is_relevant`` returns True iff a post's text contains a clear
  financial-context signal (cashtag, or a token from the company name).
- ``resolve_company_name`` looks up the longName via yfinance, cached.

Long, distinctive symbols (4+ chars, not on the collision list) bypass the
filter entirely so US tickers like ``AAPL``/``NVDA``/``GOOGL`` behave
identically to before.
"""

from __future__ import annotations

import functools
import logging
import re

logger = logging.getLogger(__name__)

# Symbols shorter than this always need a disambiguation signal.
_AMBIGUOUS_THRESHOLD = 4

# Known English / economic / geographic words that also happen to be tickers.
# Add new entries here as we discover collisions in production.
_KNOWN_WORD_SYMBOLS = frozenset(
    {
        # English words
        "ALL", "OPEN", "GOOD", "REAL", "TRUE", "FAST", "WELL", "BEST",
        "BIG", "LOW", "ONE", "TWO", "OLD", "NEW", "FREE", "LIFE", "HOME",
        "LOVE", "WIN", "PLAY", "WORK", "GROW", "STAR", "TIME", "PLUS",
        # Economic indicators
        "CPI", "GDP", "PPI", "PCE", "JOBS",
        # Geographies / orgs
        "USA", "USD", "EUR", "GBP", "JPY", "ZAR",
        # Two-letter Reddit greetings / common abbreviations
        "GM", "GE", "HD", "MO", "KO", "KR", "PG", "BA", "GS",
    }
)

_COMPANY_NAME_STOPWORDS = frozenset(
    {
        "the", "of", "and", "for", "a", "an",
        "inc", "inc.", "corp", "corp.", "corporation",
        "co", "co.", "company", "companies",
        "ltd", "ltd.", "limited",
        "plc", "sa", "ag", "nv", "n.v.", "n.v",
        "holdings", "holding", "group", "international", "global",
        "bank", "banks", "financial",  # too generic to disambiguate alone
    }
)

_TOKEN_SPLIT = re.compile(r"[\s,/\-\.&()]+")


def symbol_root(ticker: str) -> str:
    """Strip exchange suffix and uppercase. ``NPN.JO`` -> ``NPN``."""
    return (ticker or "").split(".")[0].upper()


def is_ambiguous(symbol: str) -> bool:
    """Return True if a symbol is short enough or wordy enough to need
    a contextual signal before counting a text match as the company."""
    sym = symbol_root(symbol)
    if not sym:
        return True
    return len(sym) < _AMBIGUOUS_THRESHOLD or sym in _KNOWN_WORD_SYMBOLS


def company_tokens(company_name: str | None) -> list[str]:
    """Return lowercased, ≥4-char, non-stopword tokens from a company name.

    Used as the body-text disambiguator: a post that mentions ``capitec``
    in its body is overwhelmingly likely to be about Capitec the bank,
    not CPI the macro index.
    """
    if not company_name:
        return []
    out: list[str] = []
    for raw in _TOKEN_SPLIT.split(company_name):
        tok = raw.strip().lower()
        if len(tok) >= 4 and tok not in _COMPANY_NAME_STOPWORDS:
            out.append(tok)
    return out


def post_is_relevant(
    symbol: str,
    company_name: str | None,
    text_blob: str,
) -> bool:
    """Return True if a post's text plausibly discusses the company.

    Decision tree:
      1. Distinctive symbol (≥4 chars, not on collision list): pass.
      2. Cashtag ``$SYMBOL`` (case-insensitive) in text: pass.
      3. A company-name token (≥4 chars) appears in text: pass.
      4. Otherwise: filter out.
    """
    sym = symbol_root(symbol)
    text = (text_blob or "").lower()
    if not text:
        return False
    if not is_ambiguous(sym):
        return True
    if f"${sym.lower()}" in text:
        return True
    tokens = company_tokens(company_name)
    if any(tok in text for tok in tokens):
        return True
    return False


@functools.lru_cache(maxsize=512)
def resolve_company_name(ticker: str) -> str | None:
    """Resolve a ticker to its longName/shortName via yfinance, cached.

    Returns None if yfinance cannot resolve the ticker. Callers should
    gracefully fall back to cashtag-only filtering when None is returned.
    """
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info or {}
    except Exception as exc:
        logger.warning("Could not resolve company name for %s: %s", ticker, exc)
        return None
    return info.get("longName") or info.get("shortName") or None
