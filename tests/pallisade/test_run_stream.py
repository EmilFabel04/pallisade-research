"""POST /runs enqueues; GET /runs/{id}/stream tails the durable log."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from pallisade_core.documents.models import ProcessingJob
from pallisade_core.runs import events as ev
from pallisade_core.runs import service as runs_service
from web.api.routers import runs as runs_mod
from web.api.routers.auth import router as auth_router
from web.api.routers.runs import router as runs_router


@pytest.fixture(autouse=True)
def _stream_reads_test_session(monkeypatch, session_factory_for_db):
    """The SSE generator opens its own session (it outlives the request).

    Without this the generator would use the real factory and see NOTHING:
    the `db` fixture's rows live in an uncommitted SAVEPOINT.
    `session_factory_for_db` comes from conftest.py (added in Task 3).
    """
    monkeypatch.setattr(
        runs_mod, "_stream_session_factory", lambda: session_factory_for_db
    )


@pytest.fixture()
async def client_dbg(client_for, make_user, db):
    make_user(email="stream@example.com", password="Pass!1234567")
    db.flush()
    async with client_for([("/api/auth", auth_router), ("/api", runs_router)]) as c:
        await c.post("/api/auth/login",
                     json={"email": "stream@example.com", "password": "Pass!1234567"})
        yield c


async def test_create_run_enqueues_job_and_executes_nothing(client_dbg, db):
    r = await client_dbg.post("/api/runs", json={"ticker": "NVDA", "trade_date": "2026-07-15"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    job = db.execute(
        select(ProcessingJob).where(ProcessingJob.job_type == "run_debate")
    ).scalars().one()
    assert job.payload["run_id"] == run_id
    assert job.max_attempts == 1
    assert job.status == "queued"


async def test_stream_replays_persisted_events_for_finished_run(client_dbg, db):
    from pallisade_core.users import service as users_service
    user = users_service.find_by_email(db, "stream@example.com")
    row = runs_service.create_public_run(db, user=user, ticker="NVDA", params={})
    db.flush()
    ev.append_event(db, run_id=row.id, seq=1, type="turn",
                    payload={"phase": "invest", "speaker": "bull", "round": 1, "text": "up"})
    ev.append_event(db, run_id=row.id, seq=2, type="done", payload={"reports": []})
    runs_service.mark_status(db, run=row, status="done")
    db.flush()

    r = await client_dbg.get(f"/api/runs/{row.id}/stream")
    assert r.status_code == 200
    body = r.text
    assert "event: turn" in body
    assert "id: 1" in body
    assert '"speaker": "bull"' in body or '"speaker":"bull"' in body
    assert "event: close" in body


async def test_stream_resumes_from_last_event_id(client_dbg, db):
    from pallisade_core.users import service as users_service
    user = users_service.find_by_email(db, "stream@example.com")
    row = runs_service.create_public_run(db, user=user, ticker="NVDA", params={})
    db.flush()
    for i, text in ((1, "first"), (2, "second")):
        ev.append_event(db, run_id=row.id, seq=i, type="turn",
                        payload={"phase": "invest", "speaker": "bull", "round": 1, "text": text})
    runs_service.mark_status(db, run=row, status="done")
    db.flush()

    r = await client_dbg.get(f"/api/runs/{row.id}/stream", headers={"Last-Event-ID": "1"})
    assert "second" in r.text
    assert "first" not in r.text  # already seen — must NOT be re-delivered


async def test_stream_404s_for_unknown_run(client_dbg):
    import uuid
    r = await client_dbg.get(f"/api/runs/{uuid.uuid4()}/stream")
    assert r.status_code == 404
