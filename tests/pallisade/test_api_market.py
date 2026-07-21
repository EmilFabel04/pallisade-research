"""API tests for the read-only market-quotes endpoint."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web.api.deps import get_current_user
from web.api.routers import market


@pytest.fixture()
def api(monkeypatch):
    """Client with yfinance stubbed out at the service seam."""

    def fake_fetch_quotes(symbols, **_kwargs):
        return [
            {
                "ticker": s,
                "name": f"{s} Inc.",
                "price": 100.0,
                "changePct": 1.5,
                "marketCap": "1.23T",
                "pe": 20.0,
                "spark": [99.0, 100.0],
                "ok": True,
            }
            if s != "ZZZZ"
            else {"ticker": s, "ok": False, "error": "not_found"}
            for s in symbols
        ]

    monkeypatch.setattr(market, "fetch_quotes", fake_fetch_quotes)

    app = FastAPI()
    app.include_router(market.router, prefix="/api/market")
    app.dependency_overrides[get_current_user] = lambda: object()
    return TestClient(app)


def test_quotes_returns_one_entry_per_symbol(api):
    r = api.get("/api/market/quotes", params={"symbols": "aapl,nvda"})
    assert r.status_code == 200
    quotes = r.json()["quotes"]
    assert [q["ticker"] for q in quotes] == ["AAPL", "NVDA"]
    assert quotes[0]["marketCap"] == "1.23T"


def test_quotes_marks_unresolvable_symbol_without_failing_the_batch(api):
    r = api.get("/api/market/quotes", params={"symbols": "AAPL,ZZZZ"})
    assert r.status_code == 200
    quotes = r.json()["quotes"]
    assert quotes[0]["ok"] is True
    assert quotes[1] == {"ticker": "ZZZZ", "ok": False, "error": "not_found"}


def test_quotes_with_no_symbols_returns_empty_list(api):
    r = api.get("/api/market/quotes", params={"symbols": ""})
    assert r.status_code == 200
    assert r.json() == {"quotes": []}


def test_quotes_caps_the_batch(api):
    raw = ",".join(f"SYM{i}" for i in range(80))
    r = api.get("/api/market/quotes", params={"symbols": raw})
    assert r.status_code == 200
    assert len(r.json()["quotes"]) == 50


def test_market_router_is_mounted_in_main_app():
    from web.api.main import app

    assert "/api/market/quotes" in set(app.openapi()["paths"])
