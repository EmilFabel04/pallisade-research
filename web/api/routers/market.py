"""Read-only live market data. No persistence — a pure passthrough to yfinance."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from pallisade_core.users.models import User
from web.api.deps import get_current_user
from web.api.services.market_quotes import fetch_quotes, normalize_symbols

router = APIRouter(tags=["market"])


@router.get("/quotes")
def get_quotes(
    symbols: str = Query(default="", description="Comma-separated tickers, e.g. AAPL,NVDA"),
    _: User = Depends(get_current_user),
) -> dict:
    """Batch-quote every requested symbol. Sync def: yfinance blocks."""
    return {"quotes": fetch_quotes(normalize_symbols(symbols))}
