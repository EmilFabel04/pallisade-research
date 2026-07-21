"""Tests for GET /api/library/documents, /api/library/documents/{id}, /api/library/tickers."""
from __future__ import annotations

import pytest

from pallisade_core.library.models import LibraryDocument
from pallisade_core.runs.models import EvaluationRun


# ---------------------------------------------------------------------------
# Fixture: ingested_library_factory
# Creates a LibraryDocument (via direct DB insert — no embedder needed for
# router tests) and returns it.
# ---------------------------------------------------------------------------

@pytest.fixture()
def lib_doc_factory(db, make_user):
    """Insert a LibraryDocument directly (no embedding — router tests don't need it)."""

    def _make(
        *,
        ticker: str = "NPN.JO",
        kind: str = "final_trade_decision",
        title: str | None = None,
        body_md: str = "Dummy body.",
    ) -> LibraryDocument:
        owner = make_user()
        run = EvaluationRun(mode="public", user_id=owner.id, ticker=ticker, status="done")
        db.add(run)
        db.flush()
        doc = LibraryDocument(
            run_id=run.id,
            ticker=ticker,
            kind=kind,
            title=title or f"{ticker} — {kind}",
            body_md=body_md,
        )
        db.add(doc)
        db.flush()
        return doc

    return _make


# ---------------------------------------------------------------------------
# Test 1 — list returns docs from any logged-in user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_returns_memos_for_any_logged_in_user(client_for, db, make_user, lib_doc_factory):
    from web.api.routers.library import router as library_router
    from web.api.deps import get_current_user

    lib_doc_factory(ticker="NPN.JO")
    lib_doc_factory(ticker="AGL.JO")

    viewer = make_user()  # different user from document owners
    client = client_for([("/api", library_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: viewer

    r = await client.get("/api/library/documents?limit=10")
    assert r.status_code == 200
    body = r.json()
    tickers = {it["ticker"] for it in body["items"]}
    assert "NPN.JO" in tickers
    assert "AGL.JO" in tickers
    assert len(body["items"]) >= 2


# ---------------------------------------------------------------------------
# Test 2 — list filters by ticker and kind
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_filters_by_ticker_and_kind(client_for, db, make_user, lib_doc_factory):
    from web.api.routers.library import router as library_router
    from web.api.deps import get_current_user

    lib_doc_factory(ticker="NPN.JO", kind="market_report")
    lib_doc_factory(ticker="AGL.JO", kind="market_report")

    viewer = make_user()
    client = client_for([("/api", library_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: viewer

    # Filter by ticker
    r = await client.get("/api/library/documents?ticker=NPN.JO")
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(it["ticker"] == "NPN.JO" for it in items)
    assert len(items) >= 1

    # Filter by kind
    r2 = await client.get("/api/library/documents?kind=market_report")
    assert r2.status_code == 200
    items2 = r2.json()["items"]
    assert all(it["kind"] == "market_report" for it in items2)

    # Both filters combined
    r3 = await client.get("/api/library/documents?ticker=AGL.JO&kind=market_report")
    assert r3.status_code == 200
    items3 = r3.json()["items"]
    assert all(it["ticker"] == "AGL.JO" for it in items3)


# ---------------------------------------------------------------------------
# Test 3 — get-by-id 404 on missing doc
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_by_id_404_on_missing(client_for, db, make_user):
    from web.api.routers.library import router as library_router
    from web.api.deps import get_current_user

    viewer = make_user()
    client = client_for([("/api", library_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: viewer

    r = await client.get("/api/library/documents/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Test 4 — get-by-id returns doc with body_md and source_run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_by_id_returns_full_document(client_for, db, make_user, lib_doc_factory):
    from web.api.routers.library import router as library_router
    from web.api.deps import get_current_user

    doc = lib_doc_factory(ticker="SOL.JO", body_md="Full body content here.")

    viewer = make_user()
    client = client_for([("/api", library_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: viewer

    r = await client.get(f"/api/library/documents/{doc.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(doc.id)
    assert body["ticker"] == "SOL.JO"
    assert body["body_md"] == "Full body content here."
    assert "source_run" in body
    assert body["source_run"]["id"] == str(doc.run_id)


# ---------------------------------------------------------------------------
# Test 5 — tickers endpoint returns counts
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Test 6 — q filter returns only matching docs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_q_filter_returns_matching_docs(client_for, db, make_user, lib_doc_factory):
    from web.api.routers.library import router as library_router
    from web.api.deps import get_current_user

    lib_doc_factory(ticker="NPN.JO", title="NPN Naspers deep dive")
    lib_doc_factory(ticker="AGL.JO", title="Anglo American overview")

    viewer = make_user()
    client = client_for([("/api", library_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: viewer

    r = await client.get("/api/library/documents?q=NPN")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert all("NPN" in it["title"] or "NPN" in it["ticker"] for it in items)
    titles = [it["title"] for it in items]
    assert "Anglo American overview" not in titles


# ---------------------------------------------------------------------------
# Test 7 — bad cursor returns 400
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bad_cursor_returns_400(client_for, db, make_user):
    from web.api.routers.library import router as library_router
    from web.api.deps import get_current_user

    viewer = make_user()
    client = client_for([("/api", library_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: viewer

    r = await client.get("/api/library/documents?cursor=not-a-real-cursor")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Test 5 — tickers endpoint returns counts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tickers_returns_counts(client_for, db, make_user, lib_doc_factory):
    from web.api.routers.library import router as library_router
    from web.api.deps import get_current_user

    lib_doc_factory(ticker="NPN.JO", kind="market_report")
    lib_doc_factory(ticker="NPN.JO", kind="investment_plan")
    lib_doc_factory(ticker="AGL.JO", kind="market_report")

    viewer = make_user()
    client = client_for([("/api", library_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: viewer

    r = await client.get("/api/library/tickers")
    assert r.status_code == 200
    tickers_list = r.json()["tickers"]
    counts = {row["ticker"]: row["count"] for row in tickers_list}
    assert counts.get("NPN.JO", 0) >= 2
    assert counts.get("AGL.JO", 0) >= 1
