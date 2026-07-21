"""Tests for run-completion DB persistence and library ingest hook.

Slice 1's in-process `_finalize_run_in_db` (on the router) is gone — the
durable worker owns finalization now (`pallisade_worker.debate_runner._finalize`,
Task 4). These tests migrate to call that worker-side equivalent directly,
injecting the shared `session_factory_for_db` fixture so it sees this test's
SAVEPOINT transaction instead of opening a real connection.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from pallisade_core.library import service as lib_service
from pallisade_core.library.models import LibraryDocument
from pallisade_core.rag.embeddings import FakeEmbedder
from pallisade_core.runs.models import EvaluationRun
from pallisade_worker import debate_runner
from web.api.routers.auth import router as auth_router
from web.api.routers.runs import router as runs_router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPORTS = {
    "final_trade_decision": "BUY",
    "market_report": "alpha",
}


# ---------------------------------------------------------------------------
# Test 1: success path persists DB status + ingests library
# ---------------------------------------------------------------------------


@pytest.fixture()
async def client_completion(client_for, make_user, db):
    make_user(email="comp@example.com", password="Pass!1234567")
    db.flush()
    async with client_for([("/api/auth", auth_router), ("/api", runs_router)]) as c:
        await c.post("/api/auth/login", json={"email": "comp@example.com", "password": "Pass!1234567"})
        yield c


async def test_public_run_completion_persists_db_status_and_ingests_library(
    client_completion, db, monkeypatch, session_factory_for_db
):
    """After debate_runner._finalize(success=True), DB row is 'done' and library docs are created."""
    fake = FakeEmbedder(dim=1024)
    monkeypatch.setattr(lib_service, "build_default_embedder", lambda: fake)

    # Create a DB-backed run via the API — it enqueues only, executes nothing.
    r = await client_completion.post(
        "/api/runs", json={"ticker": "NPN.JO", "trade_date": "2026-05-27"}
    )
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]

    row_before = db.get(EvaluationRun, uuid.UUID(run_id))
    assert row_before is not None

    # Call the worker's finalize helper directly, injecting the test session so
    # it sees the same SAVEPOINT transaction used by client_completion / db.
    debate_runner._finalize(
        session_factory_for_db, uuid.UUID(run_id), result=REPORTS, success=True
    )

    db.expire(row_before)
    row_after = db.get(EvaluationRun, uuid.UUID(run_id))

    assert row_after is not None
    assert row_after.status == "done"
    assert row_after.artifacts_root_key == f"runs/{row_after.id}/"

    # Library: 2 non-empty report bodies → 2 LibraryDocument rows.
    docs = db.execute(
        select(LibraryDocument).where(LibraryDocument.run_id == uuid.UUID(run_id))
    ).scalars().all()
    assert len(docs) == 2  # "final_trade_decision" + "market_report"


# ---------------------------------------------------------------------------
# Test 2: failure path persists DB status 'failed'
# ---------------------------------------------------------------------------


async def test_public_run_failure_persists_db_status_failed(
    client_completion, db, session_factory_for_db
):
    """After debate_runner._finalize(success=False), DB row is 'failed' with error_message."""
    r = await client_completion.post(
        "/api/runs", json={"ticker": "NPN.JO", "trade_date": "2026-05-27"}
    )
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]

    row_before = db.get(EvaluationRun, uuid.UUID(run_id))
    assert row_before is not None

    debate_runner._finalize(
        session_factory_for_db, uuid.UUID(run_id),
        result=None, success=False, error="boom",
    )

    db.expire(row_before)
    row_after = db.get(EvaluationRun, uuid.UUID(run_id))

    assert row_after is not None
    assert row_after.status == "failed"
    assert row_after.error_message == "boom"
