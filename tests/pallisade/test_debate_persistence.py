"""Persistence for public debate runs: reports (incremental) + result."""
from __future__ import annotations

import pytest
from sqlalchemy import inspect

from pallisade_core.runs.models import EvaluationRun
from pallisade_core.runs import service as runs_service


def test_evaluation_runs_has_reports_and_result_columns(_migrate, db):
    cols = {c["name"] for c in inspect(db.get_bind()).get_columns("evaluation_runs")}
    assert "reports" in cols
    assert "result" in cols


def test_reports_defaults_to_empty_dict(db, make_user):
    user = make_user()
    row = runs_service.create_public_run(db, user=user, ticker="NVDA")
    db.flush()
    db.refresh(row)
    assert row.reports == {}
    assert row.result is None


def test_create_public_run_stores_params(db, make_user):
    user = make_user()
    row = runs_service.create_public_run(
        db, user=user, ticker="NVDA",
        params={"trade_date": "2026-07-14", "analysts": ["market"], "asset_type": "stock"},
    )
    db.flush()
    db.refresh(row)
    assert row.params["trade_date"] == "2026-07-14"
    assert row.params["analysts"] == ["market"]


def test_append_report_accumulates(db, make_user):
    user = make_user()
    row = runs_service.create_public_run(db, user=user, ticker="NVDA")
    db.flush()
    runs_service.append_report(db, run=row, key="market_report", content="alpha")
    runs_service.append_report(db, run=row, key="news_report", content="beta")
    db.flush()
    db.refresh(row)
    assert row.reports == {"market_report": "alpha", "news_report": "beta"}


def test_save_result_sets_result(db, make_user):
    user = make_user()
    row = runs_service.create_public_run(db, user=user, ticker="NVDA")
    db.flush()
    runs_service.save_result(db, run=row, result={"final_trade_decision": "BUY"})
    db.flush()
    db.refresh(row)
    assert row.result == {"final_trade_decision": "BUY"}


from web.api.routers.auth import router as auth_router
from web.api.routers.runs import router as runs_router


@pytest.fixture()
async def client_dbg(client_for, make_user, db):
    make_user(email="dbg@example.com", password="Pass!1234567")
    db.flush()
    async with client_for([("/api/auth", auth_router), ("/api", runs_router)]) as c:
        await c.post("/api/auth/login", json={"email": "dbg@example.com", "password": "Pass!1234567"})
        yield c


async def test_get_run_serves_persisted_reports(client_dbg, db):
    # Create a public run row directly and populate persisted reports/result/params.
    from pallisade_core.users import service as users_service
    user = users_service.find_by_email(db, "dbg@example.com")
    row = runs_service.create_public_run(
        db, user=user, ticker="NVDA",
        params={"trade_date": "2026-07-14", "asset_type": "stock", "analysts": ["market"]},
    )
    db.flush()
    runs_service.append_report(db, run=row, key="market_report", content="alpha")
    runs_service.save_result(db, run=row, result={"final_trade_decision": "BUY"})
    runs_service.mark_status(db, run=row, status="done")
    db.flush()

    r = await client_dbg.get(f"/api/runs/{row.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["reports"]["market_report"] == "alpha"
    assert body["final_state"]["final_trade_decision"] == "BUY"
    assert body["trade_date"] == "2026-07-14"
    assert body["analysts"] == ["market"]
