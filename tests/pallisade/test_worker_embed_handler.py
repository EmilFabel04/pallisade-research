from pallisade_core.deals.models import Deal
from pallisade_core.documents import service as docs_service
from pallisade_core.documents.models import Document, DocumentChunk, ProcessingJob
from pallisade_core.rag.embeddings import FakeEmbedder
from pallisade_worker.handlers.embed import handle_embed, EmbedContext


def _seed_doc_with_chunks(db, user):
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=user.id, status="screening")
    db.add(deal); db.flush()
    doc = docs_service.create_document(db, deal=deal, uploader=user,
        filename="a.pdf", content_type="application/pdf",
        data=b"aaa", source_kind="pdf_text")
    db.flush()
    doc.status = "embedding"
    for i, text in enumerate(["alpha", "beta", "gamma"]):
        db.add(DocumentChunk(
            document_id=doc.id, deal_id=deal.id, chunk_index=i,
            text=text, token_count=1, page_from=1, page_to=1,
        ))
    db.flush()
    job = ProcessingJob(job_type="embed_document", document_id=doc.id)
    db.add(job); db.flush()
    return doc, job


def test_handle_embed_fills_all_null_embeddings(db, make_user):
    u = make_user()
    doc, job = _seed_doc_with_chunks(db, u)
    fake = FakeEmbedder(dim=1024)

    handle_embed(db, job, doc, ctx=EmbedContext(embedder=fake, batch_size=2))
    db.refresh(doc)
    assert doc.status == "ready"
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    assert all(c.embedding is not None for c in chunks)
    assert all(len(c.embedding) == 1024 for c in chunks)
