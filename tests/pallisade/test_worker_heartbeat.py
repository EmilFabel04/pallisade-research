import time
import threading

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


def test_heartbeat_is_refreshed_during_long_handler(db, make_user):
    u = make_user()
    doc, job = _doc_with_job(db, u)
    seen_heartbeats: list = []

    def slow_handler(session, j, d):
        # Sleep long enough that the heartbeat thread should fire at least once.
        time.sleep(1.5)
        # Reload the job to see the heartbeat that the thread wrote.
        from sqlalchemy import select
        from pallisade_core.documents.models import ProcessingJob as PJ
        fresh = session.execute(select(PJ).where(PJ.id == j.id)).scalar_one()
        seen_heartbeats.append(fresh.heartbeat_at)

    wloop.run_once(
        db, handlers={"parse_document": slow_handler}, worker_id="test:hb",
        heartbeat_interval_seconds=0.5,
    )
    # The heartbeat thread should have updated heartbeat_at at least once during the handler.
    assert seen_heartbeats and seen_heartbeats[0] is not None
