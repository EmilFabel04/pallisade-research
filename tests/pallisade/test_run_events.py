"""Durable run_events log: append, tail-from-cursor, emitter seq assignment."""
from __future__ import annotations

import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy.exc import IntegrityError

from pallisade_core.runs import events as ev
from pallisade_core.runs import service as runs_service


@pytest.fixture()
def run(db, make_user):
    user = make_user()
    row = runs_service.create_public_run(db, user=user, ticker="NVDA")
    db.flush()
    return row


def test_max_seq_zero_when_empty(db, run):
    assert ev.max_seq(db, run_id=run.id) == 0


def test_append_and_list(db, run):
    ev.append_event(db, run_id=run.id, seq=1, type="status", payload={"message": "hi"})
    db.flush()
    rows = ev.list_events(db, run_id=run.id)
    assert [(r.seq, r.type) for r in rows] == [(1, "status")]
    assert rows[0].payload == {"message": "hi"}


def test_list_events_after_cursor_excludes_seen(db, run):
    for i in (1, 2, 3):
        ev.append_event(db, run_id=run.id, seq=i, type="turn", payload={"i": i})
    db.flush()
    rows = ev.list_events(db, run_id=run.id, after_seq=2)
    assert [r.seq for r in rows] == [3]


def test_list_events_cursor_zero_returns_all(db, run):
    for i in (1, 2):
        ev.append_event(db, run_id=run.id, seq=i, type="turn", payload={})
    db.flush()
    assert [r.seq for r in ev.list_events(db, run_id=run.id, after_seq=0)] == [1, 2]


def test_list_events_ordered_by_seq(db, run):
    for i in (3, 1, 2):
        ev.append_event(db, run_id=run.id, seq=i, type="turn", payload={})
    db.flush()
    assert [r.seq for r in ev.list_events(db, run_id=run.id)] == [1, 2, 3]


def test_duplicate_seq_rejected(db, run):
    ev.append_event(db, run_id=run.id, seq=1, type="status", payload={})
    db.flush()
    ev.append_event(db, run_id=run.id, seq=1, type="status", payload={})
    with pytest.raises(IntegrityError):
        db.flush()


def test_emitter_assigns_seq_from_one(db, run, session_factory_for_db):
    emitter = ev.RunEventEmitter(run_id=run.id, session_factory=session_factory_for_db)
    assert emitter.emit("status", {"message": "a"}) == 1
    assert emitter.emit("turn", {"speaker": "bull"}) == 2
    rows = ev.list_events(db, run_id=run.id)
    assert [(r.seq, r.type) for r in rows] == [(1, "status"), (2, "turn")]


def test_emitter_resumes_after_existing_events(db, run, session_factory_for_db):
    ev.append_event(db, run_id=run.id, seq=1, type="status", payload={})
    db.flush()
    emitter = ev.RunEventEmitter(run_id=run.id, session_factory=session_factory_for_db)
    assert emitter.emit("status", {}) == 2


def test_emitter_uses_factory_not_a_shared_session(db, run):
    """Structural guard for spec §5.2 — a session per emit, each committed."""
    opened = []

    @contextmanager
    def _ctx():
        opened.append(1)
        yield db

    class _Factory:
        def __call__(self):
            return _ctx()

    emitter = ev.RunEventEmitter(run_id=run.id, session_factory=_Factory())
    emitter.emit("status", {})
    emitter.emit("status", {})
    # 1 for the initial max_seq lookup + 1 per emit.
    assert len(opened) == 3


def test_emitted_event_is_visible_from_a_separate_session(_migrate, _env):
    """Spec §5.2 behavioural guard — real commits, real second session.

    Deliberately does NOT use the `db` fixture: its SAVEPOINT rollback makes
    cross-session visibility unobservable by construction.
    """
    from pallisade_connections.models import default_org_id
    from pallisade_core.auth.hashing import hash_password
    from pallisade_core.db.session import get_session_factory
    from pallisade_core.runs.models import EvaluationRun
    from pallisade_core.users.models import User

    SF = get_session_factory()
    user_id = run_id = None
    try:
        with SF() as s:
            user = User(
                email=f"xsess{uuid.uuid4().hex[:8]}@example.com",
                name="X",
                role="member",
                password_hash=hash_password("TestPass!12345"),
                org_id=default_org_id(s),
            )
            s.add(user)
            s.flush()
            run = EvaluationRun(mode="public", user_id=user.id, ticker="NVDA", status="queued")
            s.add(run)
            s.flush()
            user_id, run_id = user.id, run.id
            s.commit()

        emitter = ev.RunEventEmitter(run_id=run_id, session_factory=SF)
        emitter.emit("turn", {"speaker": "bull", "text": "visible mid-run"})

        # A DIFFERENT session must see it immediately — no outer commit involved.
        with SF() as reader:
            rows = ev.list_events(reader, run_id=run_id)
            assert [r.type for r in rows] == ["turn"]
            assert rows[0].payload["text"] == "visible mid-run"
    finally:
        with SF() as s:
            if run_id is not None:
                s.query(ev.RunEvent).filter(ev.RunEvent.run_id == run_id).delete()
                s.query(EvaluationRun).filter(EvaluationRun.id == run_id).delete()
            if user_id is not None:
                s.query(User).filter(User.id == user_id).delete()
            s.commit()
