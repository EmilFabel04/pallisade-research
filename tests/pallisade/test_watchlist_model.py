"""Schema-level tests for the watchlist_items table."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from pallisade_core.watchlist.models import WatchlistItem


def test_insert_defaults_id_created_at_and_note(db, make_user):
    user = make_user(email="w1@example.com", password="Pass!1234567")
    db.flush()

    row = WatchlistItem(user_id=user.id, ticker="AAPL", name="Apple Inc.", conviction="bull")
    db.add(row)
    db.flush()

    assert row.id is not None
    assert row.created_at is not None
    assert row.note == ""


def test_duplicate_ticker_for_same_user_is_rejected(db, make_user):
    user = make_user(email="w2@example.com", password="Pass!1234567")
    db.flush()

    db.add(WatchlistItem(user_id=user.id, ticker="NVDA", name="NVIDIA Corp.", conviction="watch"))
    db.flush()
    db.add(WatchlistItem(user_id=user.id, ticker="NVDA", name="NVIDIA Corp.", conviction="bear"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_same_ticker_for_two_users_is_allowed(db, make_user):
    a = make_user(email="w3a@example.com", password="Pass!1234567")
    b = make_user(email="w3b@example.com", password="Pass!1234567")
    db.flush()

    db.add(WatchlistItem(user_id=a.id, ticker="MSFT", name="Microsoft Corp.", conviction="watch"))
    db.add(WatchlistItem(user_id=b.id, ticker="MSFT", name="Microsoft Corp.", conviction="bull"))
    db.flush()  # must not raise


def test_invalid_conviction_is_rejected(db, make_user):
    user = make_user(email="w4@example.com", password="Pass!1234567")
    db.flush()

    db.add(WatchlistItem(user_id=user.id, ticker="TSLA", name="Tesla", conviction="sideways"))
    with pytest.raises(IntegrityError):
        db.flush()
