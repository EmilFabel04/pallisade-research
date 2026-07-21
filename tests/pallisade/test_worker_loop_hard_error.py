from __future__ import annotations

from pallisade_core.documents.models import Document, ProcessingJob
from pallisade_core.errors import HardError
from pallisade_worker.loop import run_once
from pallisade_core.deals.models import Deal


def _doc_with_job(db, user):
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=user.id, status="screening")
    db.add(deal); db.flush()
    doc = Document(deal_id=deal.id, uploader_id=user.id, filename="a.pdf",
                   storage_key="k", content_type="application/pdf", byte_size=1,
                   sha256="s", source_kind="pdf_text")
    db.add(doc); db.flush()
    job = ProcessingJob(job_type="parse_document", document_id=doc.id,
                        attempts=0, max_attempts=3)
    db.add(job); db.flush()
    return doc, job


def test_run_once_does_not_requeue_on_hard_error(db, make_user):
    u = make_user()
    doc, job = _doc_with_job(db, u)

    def bad(session, j, d):
        raise HardError("corrupt file, do not retry")

    run_once(db, handlers={"parse_document": bad}, worker_id="test")
    db.refresh(job)
    assert job.status == "failed"
    assert "do not retry" in (job.error_message or "")
    assert job.attempts == 1
    db.refresh(doc)
    assert doc.status == "failed"


def test_run_once_still_requeues_on_generic_exception(db, make_user):
    u = make_user()
    doc, job = _doc_with_job(db, u)

    def transient(session, j, d):
        raise RuntimeError("connection reset")

    run_once(db, handlers={"parse_document": transient}, worker_id="test")
    db.refresh(job)
    assert job.status == "queued"
    assert job.attempts == 1
