from sqlalchemy import select

from pallisade_core.deals.models import Deal
from pallisade_core.documents.models import Document, ProcessingJob


def test_job_default_state(db, make_user):
    u = make_user()
    deal = Deal(name="x", target_company="y", deal_type="lbo",
                deal_lead_id=u.id, status="screening")
    db.add(deal); db.flush()
    doc = Document(deal_id=deal.id, uploader_id=u.id, filename="a.pdf",
                   storage_key="k", content_type="application/pdf",
                   byte_size=1, sha256="s", source_kind="pdf_text")
    db.add(doc); db.flush()
    job = ProcessingJob(job_type="parse_document", document_id=doc.id)
    db.add(job); db.flush()
    fetched = db.execute(select(ProcessingJob).where(ProcessingJob.id == job.id)).scalar_one()
    assert fetched.status == "queued"
    assert fetched.attempts == 0
    assert fetched.max_attempts == 3
