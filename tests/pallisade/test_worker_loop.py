from datetime import datetime, timedelta, timezone

from pallisade_core.deals.models import Deal
from pallisade_core.documents.models import Document, ProcessingJob
from pallisade_worker import loop as wloop


def _doc_with_job(db, user):
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=user.id, status="screening")
    db.add(deal); db.flush()
    doc = Document(deal_id=deal.id, uploader_id=user.id, filename="a.pdf",
                   storage_key="k", content_type="application/pdf", byte_size=1,
                   sha256="s", source_kind="pdf_text")
    db.add(doc); db.flush()
    job = ProcessingJob(job_type="parse_document", document_id=doc.id)
    db.add(job); db.flush()
    return doc, job


def test_run_once_claims_and_runs_handler(db, make_user):
    u = make_user()
    doc, job = _doc_with_job(db, u)
    called = []

    def handler(session, j, d):
        called.append((j.id, d.id))

    wloop.run_once(db, handlers={"parse_document": handler}, worker_id="test:1")
    db.refresh(job)
    assert job.status == "done"
    assert job.completed_at is not None
    assert called == [(job.id, doc.id)]


def test_run_once_marks_failed_then_requeues_within_max_attempts(db, make_user):
    u = make_user()
    doc, job = _doc_with_job(db, u)

    def boom(session, j, d):
        raise RuntimeError("nope")

    wloop.run_once(db, handlers={"parse_document": boom}, worker_id="test:1")
    db.refresh(job)
    assert job.status == "queued"
    assert job.attempts == 1
    assert job.error_message == "nope"


def test_run_once_marks_failed_after_max_attempts(db, make_user):
    u = make_user()
    doc, job = _doc_with_job(db, u)
    job.attempts = 2  # one more attempt allowed

    def boom(session, j, d):
        raise RuntimeError("still nope")

    wloop.run_once(db, handlers={"parse_document": boom}, worker_id="test:1")
    db.refresh(job)
    db.refresh(doc)
    assert job.status == "failed"
    assert doc.status == "failed"
    assert doc.error_message == "still nope"


def test_reaper_requeues_stale_running_jobs(db, make_user):
    u = make_user()
    doc, job = _doc_with_job(db, u)
    job.status = "running"
    job.locked_by = "ghost"
    job.heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=120)
    db.flush()

    wloop.reap_zombies(db, stale_after_seconds=60)
    db.refresh(job)
    assert job.status == "queued"
    assert job.locked_by is None
