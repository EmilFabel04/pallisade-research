"""Worker debate runner: emits status/report/turn/done in order, persists, finalizes.

Uses a fake graph — no LLM calls, no network.

`session_factory_for_db` comes from tests/pallisade/conftest.py (added in Task 3).
"""
from __future__ import annotations

import uuid

import pytest

from pallisade_core.runs import events as ev
from pallisade_core.runs import service as runs_service
from pallisade_worker import debate_runner


class _FakeGraphInner:
    def __init__(self, chunks):
        self._chunks = chunks

    def stream(self, init_state, **kwargs):
        yield from self._chunks


class _FakeGraph:
    def __init__(self, chunks):
        self.graph = _FakeGraphInner(chunks)
        self.curr_state = None
        self.memory_log = self
        self.propagator = self

    # memory_log
    def get_past_context(self, ticker):
        return ""

    def store_decision(self, **kw):
        return None

    # propagator
    def create_initial_state(self, ticker, trade_date, asset_type="stock", past_context=""):
        return {}

    def get_graph_args(self, callbacks=None):
        return {"stream_mode": "values", "config": {}}

    def _log_state(self, trade_date, final_state):
        return None


def _factory_for(chunks):
    def _make(*, analysts, analysts_only=False, config, callbacks):
        return _FakeGraph(chunks)
    return _make


@pytest.fixture()
def run(db, make_user):
    user = make_user()
    row = runs_service.create_public_run(
        db, user=user, ticker="NVDA",
        params={"trade_date": "2026-07-15", "asset_type": "stock", "analysts": ["market"]},
    )
    db.flush()
    return row


def test_emits_turns_and_reports_in_order(db, run, monkeypatch, session_factory_for_db):
    monkeypatch.setattr(debate_runner, "_ingest_library", lambda *a, **kw: None)
    chunks = [
        {"market_report": "MKT"},
        {"market_report": "MKT",
         "investment_debate_state": {"count": 1, "current_response": "Bull Analyst: up"}},
        {"market_report": "MKT",
         "investment_debate_state": {"count": 2, "current_response": "Bear Analyst: down"}},
        {"market_report": "MKT", "final_trade_decision": "BUY",
         "investment_debate_state": {"count": 2, "current_response": "Bear Analyst: down"}},
    ]
    debate_runner.run_debate(
        run_id=run.id,
        session_factory=session_factory_for_db,
        graph_factory=_factory_for(chunks),
    )
    rows = ev.list_events(db, run_id=run.id)
    kinds = [r.type for r in rows]
    assert "turn" in kinds and "report" in kinds
    assert kinds[-1] == "done"
    turns = [r.payload for r in rows if r.type == "turn"]
    assert [(t["speaker"], t["round"], t["text"]) for t in turns] == [
        ("bull", 1, "up"), ("bear", 1, "down"),
    ]


def test_seq_is_dense_and_starts_at_one(db, run, monkeypatch, session_factory_for_db):
    monkeypatch.setattr(debate_runner, "_ingest_library", lambda *a, **kw: None)
    chunks = [{"market_report": "MKT"}]
    debate_runner.run_debate(
        run_id=run.id, session_factory=session_factory_for_db,
        graph_factory=_factory_for(chunks),
    )
    seqs = [r.seq for r in ev.list_events(db, run_id=run.id)]
    assert seqs == list(range(1, len(seqs) + 1))


def test_reports_persisted_and_run_marked_done(db, run, monkeypatch, session_factory_for_db):
    monkeypatch.setattr(debate_runner, "_ingest_library", lambda *a, **kw: None)
    chunks = [{"market_report": "MKT", "final_trade_decision": "BUY"}]
    debate_runner.run_debate(
        run_id=run.id, session_factory=session_factory_for_db,
        graph_factory=_factory_for(chunks),
    )
    db.refresh(run)
    assert run.reports["market_report"] == "MKT"
    assert run.result["final_trade_decision"] == "BUY"
    assert run.status == "done"


def test_done_event_is_written_before_status_flips(db, run, monkeypatch, session_factory_for_db):
    """Spec §5.3: status must not go terminal while events are unwritten."""
    monkeypatch.setattr(debate_runner, "_ingest_library", lambda *a, **kw: None)
    observed = {}
    real_finalize = debate_runner._finalize

    def _spy(sf, run_id, *, result, success, error=None):
        with sf() as s:
            observed["kinds_at_finalize"] = [r.type for r in ev.list_events(s, run_id=run_id)]
        return real_finalize(sf, run_id, result=result, success=success, error=error)

    monkeypatch.setattr(debate_runner, "_finalize", _spy)
    debate_runner.run_debate(
        run_id=run.id, session_factory=session_factory_for_db,
        graph_factory=_factory_for([{"market_report": "MKT"}]),
    )
    assert "done" in observed["kinds_at_finalize"]


def test_error_event_is_written_before_status_flips(db, run, monkeypatch, session_factory_for_db):
    """Spec §5.3, error path: status must not go terminal while events are unwritten.

    `_finalize` never writes to run_events, so a test that only checks final DB
    state (as test_failure_emits_error_then_marks_failed does) would pass even
    if the emit-then-finalize order were reversed. Spy on _finalize, as the
    success-path test does, to prove the "error" event is already durable by
    the time _finalize runs.
    """
    from pallisade_core.errors import HardError

    observed = {}
    real_finalize = debate_runner._finalize

    def _spy(sf, run_id, *, result, success, error=None):
        with sf() as s:
            observed["kinds_at_finalize"] = [r.type for r in ev.list_events(s, run_id=run_id)]
        return real_finalize(sf, run_id, result=result, success=success, error=error)

    monkeypatch.setattr(debate_runner, "_finalize", _spy)

    def _boom(*, analysts, analysts_only=False, config, callbacks):
        raise RuntimeError("graph exploded")

    with pytest.raises(HardError):
        debate_runner.run_debate(
            run_id=run.id, session_factory=session_factory_for_db, graph_factory=_boom,
        )
    assert "error" in observed["kinds_at_finalize"]


def test_failure_emits_error_then_marks_failed(db, run, monkeypatch, session_factory_for_db):
    from pallisade_core.errors import HardError

    def _boom(*, analysts, analysts_only=False, config, callbacks):
        raise RuntimeError("graph exploded")

    with pytest.raises(HardError):
        debate_runner.run_debate(
            run_id=run.id, session_factory=session_factory_for_db, graph_factory=_boom,
        )
    db.refresh(run)
    assert run.status == "failed"
    rows = ev.list_events(db, run_id=run.id)
    assert rows[-1].type == "error"
    assert "graph exploded" in rows[-1].payload["error"]


def test_partial_turns_survive_failure(db, run, monkeypatch, session_factory_for_db):
    from pallisade_core.errors import HardError

    def _chunks():
        yield {"investment_debate_state": {"count": 1, "current_response": "Bull Analyst: up"}}
        raise RuntimeError("died mid-debate")

    class _G(_FakeGraph):
        def __init__(self):
            super().__init__([])
            self.graph = type("I", (), {"stream": lambda _s, *a, **k: _chunks()})()

    with pytest.raises(HardError):
        debate_runner.run_debate(
            run_id=run.id, session_factory=session_factory_for_db,
            graph_factory=lambda **kw: _G(),
        )
    turns = [r.payload for r in ev.list_events(db, run_id=run.id) if r.type == "turn"]
    assert turns and turns[0]["speaker"] == "bull"


def test_run_debate_passes_analysts_only_to_factory(db, make_user, session_factory_for_db):
    user = make_user()
    row = runs_service.create_public_run(
        db, user=user, ticker="NVDA",
        params={"trade_date": "2026-07-15", "asset_type": "stock",
                "analysts": ["fundamentals"], "analysts_only": True},
    )
    db.flush()
    captured = {}

    def _factory(*, analysts, analysts_only, config, callbacks):
        captured["analysts_only"] = analysts_only
        captured["analysts"] = analysts
        return _FakeGraph([{"fundamentals_report": "FND"}])

    debate_runner.run_debate(
        run_id=row.id, session_factory=session_factory_for_db, graph_factory=_factory,
    )
    assert captured["analysts_only"] is True
    assert captured["analysts"] == ["fundamentals"]


def test_missing_run_raises_hard_error(db, session_factory_for_db):
    from pallisade_core.errors import HardError
    with pytest.raises(HardError):
        debate_runner.run_debate(
            run_id=uuid.uuid4(), session_factory=session_factory_for_db,
            graph_factory=_factory_for([]),
        )


def test_non_queued_run_refuses_reentry(db, run, session_factory_for_db):
    """reap_zombies (loop.py) can requeue a stale `running` job without checking
    max_attempts. If a second worker then claimed it, run_debate must refuse to
    re-run rather than append a second copy of the argument and re-spend the
    LLM budget. Because there is no live worker left for an interrupted,
    re-claimed run, run_debate must ALSO finalize the run as failed — otherwise
    stream_run's SSE loop (which only terminates on a terminal status) would
    have an open or reopened tab poll forever."""
    from pallisade_core.errors import HardError

    runs_service.mark_status(db, run=run, status="running")
    db.flush()

    with pytest.raises(HardError):
        debate_runner.run_debate(
            run_id=run.id, session_factory=session_factory_for_db,
            graph_factory=_factory_for([]),
        )
    db.refresh(run)
    assert run.status == "failed"
    rows = ev.list_events(db, run_id=run.id)
    assert len(rows) == 1
    assert rows[-1].type == "error"


def test_done_run_refuses_reentry_without_modification(db, run, session_factory_for_db):
    """A run that already reached a terminal status (done/failed) must never be
    overwritten by a stray re-claim: no re-finalization, no events appended.
    Only an interrupted `running` run (no live worker) gets finalized as failed —
    see test_non_queued_run_refuses_reentry."""
    from pallisade_core.errors import HardError

    runs_service.mark_status(db, run=run, status="done")
    db.flush()

    with pytest.raises(HardError):
        debate_runner.run_debate(
            run_id=run.id, session_factory=session_factory_for_db,
            graph_factory=_factory_for([]),
        )
    db.refresh(run)
    assert run.status == "done"
    assert ev.list_events(db, run_id=run.id) == []


def test_handler_rejects_missing_run_id(db):
    from pallisade_core.documents.models import ProcessingJob
    from pallisade_core.errors import HardError
    from pallisade_worker.handlers.debate import handle_run_debate

    job = ProcessingJob(job_type="run_debate", payload={}, status="running")
    with pytest.raises(HardError):
        handle_run_debate(db, job, None)


def test_handler_rejects_malformed_run_id(db):
    from pallisade_core.documents.models import ProcessingJob
    from pallisade_core.errors import HardError
    from pallisade_worker.handlers.debate import handle_run_debate

    job = ProcessingJob(job_type="run_debate", payload={"run_id": "nope"}, status="running")
    with pytest.raises(HardError):
        handle_run_debate(db, job, None)


def test_run_debate_registered_in_handlers():
    from pallisade_worker.__main__ import build_handlers
    assert "run_debate" in build_handlers()
