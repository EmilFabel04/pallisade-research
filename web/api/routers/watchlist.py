"""Per-user watchlist CRUD. Market fields are never stored — see routers/market.py."""
from __future__ import annotations

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from pallisade_core.users.models import User
from pallisade_core.watchlist.models import WatchlistItem
from web.api.deps import get_current_user, get_db
from web.api.services.market_quotes import quote_one

logger = logging.getLogger(__name__)

router = APIRouter(tags=["watchlist"])

Conviction = Literal["bull", "bear", "watch"]


class WatchlistCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    conviction: Conviction = "watch"
    note: str = ""


class WatchlistUpdate(BaseModel):
    conviction: Conviction | None = None
    note: str | None = None


def _view(row: WatchlistItem) -> dict:
    return {
        "id": str(row.id),
        "ticker": row.ticker,
        "name": row.name,
        "conviction": row.conviction,
        "note": row.note,
        "created_at": row.created_at.isoformat(),
    }


def _owned(db: Session, wid: uuid.UUID, user: User) -> WatchlistItem:
    row = db.get(WatchlistItem, wid)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return row


@router.get("")
def list_items(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    rows = (
        db.execute(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user.id)
            .order_by(WatchlistItem.created_at.desc())
        )
        .scalars()
        .all()
    )
    return {"items": [_view(r) for r in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_item(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ticker = payload.ticker.strip().upper()

    existing = db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id, WatchlistItem.ticker == ticker
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already on watchlist")

    try:
        # Validation only needs price + name; skip the spark-line history
        # fetch that quote_one would otherwise make and immediately discard.
        quote = quote_one(ticker, with_history=False)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unknown ticker"
        )
    except Exception:
        logger.warning("quote validation failed for %s", ticker, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="market data unavailable"
        )

    row = WatchlistItem(
        user_id=user.id,
        ticker=ticker,
        name=quote.get("name") or ticker,
        conviction=payload.conviction,
        note=payload.note,
    )
    db.add(row)
    db.flush()
    db.commit()
    return _view(row)


@router.patch("/{wid}")
def update_item(
    wid: uuid.UUID,
    payload: WatchlistUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = _owned(db, wid, user)
    if payload.conviction is not None:
        row.conviction = payload.conviction
    if payload.note is not None:
        row.note = payload.note
    db.flush()
    db.commit()
    return _view(row)


@router.delete("/{wid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    wid: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    row = _owned(db, wid, user)
    db.delete(row)
    db.flush()
    db.commit()
