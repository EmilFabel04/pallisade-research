from __future__ import annotations

import pytest

from pallisade_core.runs import service as runs


def test_create_public_run(db, make_user):
    u = make_user()
    r = runs.create_public_run(db, user=u, ticker="NVDA")
    db.flush()
    assert r.id is not None
    assert r.mode == "public"
    assert r.ticker == "NVDA"
    assert r.deal_id is None
    assert r.status == "queued"


def test_public_run_ticker_required(db, make_user):
    u = make_user()
    with pytest.raises(ValueError):
        runs.create_public_run(db, user=u, ticker="")


def test_list_for_user_returns_only_own(db, make_user):
    a, b = make_user(), make_user()
    runs.create_public_run(db, user=a, ticker="X"); db.flush()
    runs.create_public_run(db, user=b, ticker="Y"); db.flush()
    runs.create_public_run(db, user=a, ticker="Z"); db.flush()
    rows = runs.list_for_user(db, user=a)
    assert {r.ticker for r in rows} == {"X", "Z"}


def test_mark_complete(db, make_user):
    u = make_user()
    r = runs.create_public_run(db, user=u, ticker="X"); db.flush()
    runs.mark_status(db, run=r, status="done", artifacts_root_key="runs/abc/reports")
    db.flush()
    assert r.status == "done"
    assert r.completed_at is not None
    assert r.artifacts_root_key == "runs/abc/reports"
