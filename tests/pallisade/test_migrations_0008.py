from __future__ import annotations

from sqlalchemy import inspect, text


def test_run_once_handles_null_document_id_job(db, make_user):
    """A processing_jobs row with document_id=NULL must not fail-fast at the dispatcher.

    After migration 0008, evaluate_deal jobs have no document. The worker
    should pass doc=None to the handler instead of auto-failing the job.
    """
    from pallisade_core.documents.models import ProcessingJob
    from pallisade_worker.loop import run_once

    job = ProcessingJob(
        job_type="evaluate_deal", document_id=None,
        payload={"run_id": "00000000-0000-0000-0000-000000000001"},
        status="queued", attempts=0, max_attempts=1,
    )
    db.add(job); db.commit()

    received = []
    def handler(session, j, d):
        received.append((j.id, d))

    handlers = {"evaluate_deal": handler}
    processed = run_once(db, handlers=handlers, worker_id="t")
    db.commit()

    assert processed is True
    assert len(received) == 1
    assert received[0][1] is None  # doc was None, passed through


def test_evaluation_runs_has_phase3_columns(db):
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("evaluation_runs")}
    assert {"thesis", "params", "current_node"}.issubset(cols)


def test_processing_jobs_document_id_is_nullable(db):
    insp = inspect(db.bind)
    cols = {c["name"]: c for c in insp.get_columns("processing_jobs")}
    assert cols["document_id"]["nullable"] is True


def test_processing_jobs_has_payload(db):
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("processing_jobs")}
    assert "payload" in cols


def test_processing_jobs_accepts_evaluate_deal_job_type(db):
    """The CHECK constraint must allow the new job_type. Insert + commit + rollback."""
    db.execute(text(
        "INSERT INTO processing_jobs (job_type, payload, status, max_attempts) "
        "VALUES ('evaluate_deal', '{\"run_id\": \"00000000-0000-0000-0000-000000000001\"}', "
        "'queued', 1)"
    ))
    db.commit()
