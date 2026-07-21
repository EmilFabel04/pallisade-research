from __future__ import annotations

import uuid

import pytest
from web.api.routers.auth import router as auth_router
from web.api.routers.runs import router as runs_router


@pytest.fixture()
async def client_a(client_for, make_user, db):
    make_user(email="a@example.com", password="Pass!1234567"); db.flush()
    async with client_for([("/api/auth", auth_router), ("/api", runs_router)]) as c:
        await c.post("/api/auth/login", json={"email": "a@example.com", "password": "Pass!1234567"})
        yield c


async def test_create_run_records_db_row(client_a, db):
    r = await client_a.post("/api/runs", json={
        "ticker": "NVDA", "trade_date": "2026-05-25",
    })
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    from pallisade_core.runs.models import EvaluationRun
    row = db.get(EvaluationRun, uuid.UUID(run_id))
    assert row is not None and row.mode == "public" and row.ticker == "NVDA"


async def test_get_run_owner_only(client_for, make_user, db):
    a = make_user(email="a@example.com", password="Pass!1234567")
    b = make_user(email="b@example.com", password="Pass!1234567")
    db.flush()
    async with client_for([("/api/auth", auth_router), ("/api", runs_router)]) as c:
        await c.post("/api/auth/login", json={"email": "a@example.com", "password": "Pass!1234567"})
        r = await c.post("/api/runs", json={"ticker": "NVDA", "trade_date": "2026-05-25"})
        run_id = r.json()["run_id"]
        await c.post("/api/auth/logout")
        await c.post("/api/auth/login", json={"email": "b@example.com", "password": "Pass!1234567"})
        forbidden = await c.get(f"/api/runs/{run_id}")
        assert forbidden.status_code == 404


async def test_list_runs_scoped_to_caller(client_for, make_user, db):
    a = make_user(email="a@example.com", password="Pass!1234567")
    b = make_user(email="b@example.com", password="Pass!1234567")
    db.flush()
    async with client_for([("/api/auth", auth_router), ("/api", runs_router)]) as c:
        await c.post("/api/auth/login", json={"email": "a@example.com", "password": "Pass!1234567"})
        await c.post("/api/runs", json={"ticker": "NVDA", "trade_date": "2026-05-25"})
        await c.post("/api/auth/logout")
        await c.post("/api/auth/login", json={"email": "b@example.com", "password": "Pass!1234567"})
        lst = await c.get("/api/runs")
        assert lst.status_code == 200
        assert lst.json()["runs"] == []
