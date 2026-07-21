"""API tests for owner-scoped watchlist CRUD."""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web.api.deps import get_current_user, get_db
from web.api.routers import watchlist
from web.api.services.market_quotes import quote_one as real_quote_one


@pytest.fixture()
def make_api(db, make_user, monkeypatch):
    """Builds a client acting as a given user, with ticker validation stubbed."""

    def fake_quote_one(symbol, **_kwargs):
        if symbol == "ZZZZ":
            raise LookupError(symbol)
        return {"ticker": symbol, "name": f"{symbol} Inc.", "ok": True}

    monkeypatch.setattr(watchlist, "quote_one", fake_quote_one)

    def _build(user):
        app = FastAPI()
        app.include_router(watchlist.router, prefix="/api/watchlist")
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    return _build


@pytest.fixture()
def user_a(db, make_user):
    u = make_user(email="wa@example.com", password="Pass!1234567")
    db.flush()
    return u


@pytest.fixture()
def user_b(db, make_user):
    u = make_user(email="wb@example.com", password="Pass!1234567")
    db.flush()
    return u


def test_add_stores_ticker_with_resolved_name_and_defaults(make_api, user_a):
    c = make_api(user_a)
    r = c.post("/api/watchlist", json={"ticker": "aapl"})
    assert r.status_code == 201
    body = r.json()
    assert body["ticker"] == "AAPL"
    assert body["name"] == "AAPL Inc."
    assert body["conviction"] == "watch"
    assert body["note"] == ""
    assert body["id"]


def test_add_accepts_conviction_and_note(make_api, user_a):
    c = make_api(user_a)
    r = c.post("/api/watchlist", json={"ticker": "NVDA", "conviction": "bull", "note": "AI capex"})
    assert r.status_code == 201
    assert r.json()["conviction"] == "bull"
    assert r.json()["note"] == "AI capex"


def test_add_unknown_ticker_is_422(make_api, user_a):
    c = make_api(user_a)
    assert c.post("/api/watchlist", json={"ticker": "ZZZZ"}).status_code == 422


def test_add_duplicate_ticker_is_409(make_api, user_a):
    c = make_api(user_a)
    c.post("/api/watchlist", json={"ticker": "MSFT"})
    assert c.post("/api/watchlist", json={"ticker": "msft"}).status_code == 409


def test_add_rejects_invalid_conviction(make_api, user_a):
    c = make_api(user_a)
    r = c.post("/api/watchlist", json={"ticker": "AAPL", "conviction": "sideways"})
    assert r.status_code == 422


def test_add_validates_without_fetching_history(make_api, user_a, monkeypatch):
    """add_item only needs price + name; it must not pay for quote_one's
    spark-line history fetch (with_history=False)."""
    history_calls: list[str] = []

    class TrackingTicker:
        def __init__(self, symbol: str):
            self._symbol = symbol

        @property
        def info(self) -> dict:
            return {"regularMarketPrice": 100.0, "previousClose": 99.0, "longName": "Foo Inc."}

        def history(self, period: str = "1mo"):
            history_calls.append(self._symbol)
            raise AssertionError("history() should not be called when with_history=False")

    def spy_quote_one(symbol, **kwargs):
        # Exercises the real quote_one (not the fixture's stub) so we can
        # observe whether the ticker's history() was actually invoked.
        return real_quote_one(symbol, ticker_factory=TrackingTicker, **kwargs)

    c = make_api(user_a)
    monkeypatch.setattr(watchlist, "quote_one", spy_quote_one)

    r = c.post("/api/watchlist", json={"ticker": "FOO"})
    assert r.status_code == 201
    assert history_calls == []


def test_list_returns_only_own_rows_newest_first(make_api, user_a, user_b):
    ca, cb = make_api(user_a), make_api(user_b)
    ca.post("/api/watchlist", json={"ticker": "AAPL"})
    ca.post("/api/watchlist", json={"ticker": "NVDA"})
    cb.post("/api/watchlist", json={"ticker": "TSLA"})

    assert [i["ticker"] for i in ca.get("/api/watchlist").json()["items"]] == ["NVDA", "AAPL"]
    assert [i["ticker"] for i in cb.get("/api/watchlist").json()["items"]] == ["TSLA"]


def test_patch_updates_only_user_fields(make_api, user_a):
    c = make_api(user_a)
    wid = c.post("/api/watchlist", json={"ticker": "AAPL"}).json()["id"]

    r = c.patch(f"/api/watchlist/{wid}", json={"conviction": "bear", "note": "rich"})
    assert r.status_code == 200
    assert r.json()["conviction"] == "bear"
    assert r.json()["note"] == "rich"
    assert r.json()["ticker"] == "AAPL"


def test_patch_other_users_row_is_404(make_api, user_a, user_b):
    wid = make_api(user_a).post("/api/watchlist", json={"ticker": "AAPL"}).json()["id"]
    r = make_api(user_b).patch(f"/api/watchlist/{wid}", json={"conviction": "bull"})
    assert r.status_code == 404
    items = make_api(user_a).get("/api/watchlist").json()["items"]
    assert items[0]["conviction"] == "watch"


def test_patch_ignores_protected_fields(make_api, user_a):
    c = make_api(user_a)
    created = c.post("/api/watchlist", json={"ticker": "AAPL"}).json()
    wid, original_ticker, original_name = created["id"], created["ticker"], created["name"]

    r = c.patch(
        f"/api/watchlist/{wid}",
        json={
            "note": "ok",
            "ticker": "MSFT",
            "name": "hacked",
            "user_id": str(uuid.uuid4()),
            "id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["note"] == "ok"
    assert body["ticker"] == original_ticker
    assert body["name"] == original_name
    assert body["id"] == wid


def test_delete_removes_the_row(make_api, user_a):
    c = make_api(user_a)
    wid = c.post("/api/watchlist", json={"ticker": "AAPL"}).json()["id"]
    assert c.delete(f"/api/watchlist/{wid}").status_code == 204
    assert c.get("/api/watchlist").json()["items"] == []


def test_delete_other_users_row_is_404(make_api, user_a, user_b):
    wid = make_api(user_a).post("/api/watchlist", json={"ticker": "AAPL"}).json()["id"]
    assert make_api(user_b).delete(f"/api/watchlist/{wid}").status_code == 404
    assert len(make_api(user_a).get("/api/watchlist").json()["items"]) == 1


def test_unknown_id_is_404(make_api, user_a):
    c = make_api(user_a)
    assert c.delete(f"/api/watchlist/{uuid.uuid4()}").status_code == 404


def test_watchlist_router_is_mounted_in_main_app():
    from web.api.main import app

    paths = set(app.openapi()["paths"])
    assert "/api/watchlist" in paths
    assert "/api/watchlist/{wid}" in paths
