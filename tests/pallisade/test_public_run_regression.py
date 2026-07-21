"""End-to-end regression for the public-run path.

Slice 1 executed the debate synchronously in-process, so this test patched
`TradingAgentsGraph` and polled `GET /runs/{id}` until the in-process thread
finished. Now `POST /runs` only enqueues (Task 5) and the durable worker owns
execution (Task 4) — there is no in-process thread to poll for. This migrates
the test to the DB/job equivalent: enqueue via the API, then drive the
worker's `run_debate` directly with a fake graph factory (as the real worker
loop would, minus the queue-polling), and assert the same end state.
"""
from __future__ import annotations

import uuid

from unittest.mock import MagicMock
from sqlalchemy import select

from pallisade_core.documents.models import ProcessingJob
from pallisade_worker import debate_runner
from web.api.routers.auth import router as auth_router
from web.api.routers.runs import router as runs_router


class _FakeGraph:
    def __init__(self, *a, **kw):
        self.memory_log = MagicMock()
        self.memory_log.get_past_context.return_value = None
        self.propagator = MagicMock()
        self.propagator.create_initial_state.return_value = {}
        self.propagator.get_graph_args.return_value = {}
        self.graph = MagicMock()
        self.graph.stream.return_value = iter([
            {"market_report": "MR ok"},
            {"final_trade_decision": "BUY"},
        ])
        self.curr_state = None

    def _log_state(self, *_a, **_k): pass


async def test_public_run_end_to_end(client_for, make_user, db, monkeypatch, session_factory_for_db):
    monkeypatch.setattr(debate_runner, "_ingest_library", lambda *a, **kw: None)
    make_user(email="a@example.com", password="Pass!1234567"); db.flush()
    async with client_for([("/api/auth", auth_router), ("/api", runs_router)]) as c:
        await c.post("/api/auth/login", json={"email": "a@example.com", "password": "Pass!1234567"})
        r = await c.post("/api/runs", json={"ticker": "NVDA", "trade_date": "2026-05-25"})
        assert r.status_code == 200
        run_id = r.json()["run_id"]

        # POST /runs enqueues only — assert the durable job, then run the
        # worker's debate loop directly (fake graph, no LLM) to simulate the
        # worker draining that job.
        job = db.execute(
            select(ProcessingJob).where(ProcessingJob.job_type == "run_debate")
        ).scalars().one()
        assert job.payload["run_id"] == run_id

        debate_runner.run_debate(
            run_id=uuid.UUID(run_id),
            session_factory=session_factory_for_db,
            graph_factory=_FakeGraph,
        )

        detail = await c.get(f"/api/runs/{run_id}")
        assert detail.json()["status"] == "done", detail.text
        assert "market_report" in detail.json()["reports"]
        assert detail.json()["reports"]["market_report"] == "MR ok"
