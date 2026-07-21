from __future__ import annotations

import pytest
from pallisade_core.runs import service as runs_service
from pallisade_core.runs.models import EvaluationRun


def _mk(db, user, *, analysts_only):
    return runs_service.create_public_run(
        db, user=user, ticker="NVDA",
        params={"trade_date": "2026-07-20", "analysts": ["market"],
                "analysts_only": analysts_only},
    )


def test_list_for_user_filters_by_kind(db, make_user):
    user = make_user()
    _mk(db, user, analysts_only=True)
    _mk(db, user, analysts_only=False)
    _mk(db, user, analysts_only=False)
    db.flush()

    analyst_runs = runs_service.list_for_user(db, user=user, kind="analysts")
    debate_runs = runs_service.list_for_user(db, user=user, kind="debate")

    assert len(analyst_runs) == 1
    assert len(debate_runs) == 2
    assert all((r.params or {}).get("analysts_only") for r in analyst_runs)


def test_list_for_user_limit_caps_rows(db, make_user):
    user = make_user()
    for _ in range(7):
        _mk(db, user, analysts_only=False)
    db.flush()
    rows = runs_service.list_for_user(db, user=user, kind="debate", limit=5)
    assert len(rows) == 5


def test_list_for_user_no_kind_returns_all(db, make_user):
    user = make_user()
    _mk(db, user, analysts_only=True)
    _mk(db, user, analysts_only=False)
    db.flush()
    assert len(runs_service.list_for_user(db, user=user)) == 2


def test_null_params_public_run_classified_as_debate(db, make_user):
    """Pre-feature public runs have no `analysts_only` key at all (params is
    NULL, not just missing the key) — the JSONB coalesce must still route
    them to kind="debate", not kind="analysts"."""
    user = make_user()
    run = EvaluationRun(mode="public", user_id=user.id, ticker="NVDA", status="queued")
    db.add(run)
    db.flush()

    debate_runs = runs_service.list_for_user(db, user=user, kind="debate")
    analyst_runs = runs_service.list_for_user(db, user=user, kind="analysts")

    assert run.id in {r.id for r in debate_runs}
    assert run.id not in {r.id for r in analyst_runs}
