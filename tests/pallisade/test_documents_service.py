import hashlib
import io
import uuid

import pytest

from pallisade_core.deals.models import Deal
from pallisade_core.documents import service as docs_service
from pallisade_core.documents.models import Document, ProcessingJob


def _deal(db, lead):
    d = Deal(name="X", target_company="Y", deal_type="lbo",
             deal_lead_id=lead.id, status="screening")
    db.add(d); db.flush()
    return d


def test_create_document_persists_row_and_parse_job(db, make_user, tmp_path, monkeypatch):
    u = make_user()
    deal = _deal(db, u)
    payload = b"%PDF-1.7\nstuff"
    sha = hashlib.sha256(payload).hexdigest()

    doc = docs_service.create_document(
        db, deal=deal, uploader=u,
        filename="CIM.pdf", content_type="application/pdf",
        data=payload, source_kind="pdf_text",
    )
    db.flush()

    assert doc.sha256 == sha
    assert doc.byte_size == len(payload)
    assert doc.status == "pending"
    assert doc.storage_key.startswith(f"deals/{deal.id}/docs/{doc.id}/")

    # exactly one parse_document job
    jobs = db.query(ProcessingJob).filter(ProcessingJob.document_id == doc.id).all()
    assert len(jobs) == 1
    assert jobs[0].job_type == "parse_document"
    assert jobs[0].status == "queued"


def test_per_deal_sha256_dedupe_returns_409(db, make_user):
    u = make_user()
    deal = _deal(db, u)
    payload = b"hello world"

    docs_service.create_document(db, deal=deal, uploader=u,
        filename="a.pdf", content_type="application/pdf",
        data=payload, source_kind="pdf_text")
    db.flush()

    with pytest.raises(docs_service.DuplicateDocument):
        docs_service.create_document(db, deal=deal, uploader=u,
            filename="b.pdf", content_type="application/pdf",
            data=payload, source_kind="pdf_text")


def test_list_documents_excludes_soft_deleted(db, make_user):
    u = make_user()
    deal = _deal(db, u)
    a = docs_service.create_document(db, deal=deal, uploader=u,
        filename="a.pdf", content_type="application/pdf",
        data=b"aaa", source_kind="pdf_text")
    b = docs_service.create_document(db, deal=deal, uploader=u,
        filename="b.pdf", content_type="application/pdf",
        data=b"bbb", source_kind="pdf_text")
    db.flush()

    docs_service.soft_delete(db, document=a)
    db.flush()

    rows = docs_service.list_for_deal(db, deal=deal)
    assert [d.id for d in rows] == [b.id]


def test_retry_failed_resets_status_and_creates_new_parse_job(db, make_user):
    u = make_user()
    deal = _deal(db, u)
    doc = docs_service.create_document(db, deal=deal, uploader=u,
        filename="a.pdf", content_type="application/pdf",
        data=b"aaa", source_kind="pdf_text")
    db.flush()
    doc.status = "failed"
    doc.error_message = "bad scan"
    db.flush()

    docs_service.retry(db, document=doc)
    db.flush()
    assert doc.status == "pending"
    assert doc.error_message is None
    jobs = db.query(ProcessingJob).filter(
        ProcessingJob.document_id == doc.id, ProcessingJob.job_type == "parse_document"
    ).all()
    assert len(jobs) == 2  # original + retry
