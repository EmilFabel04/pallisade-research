import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from pallisade_core.deals.models import Deal
from pallisade_core.documents.models import Document, DocumentChunk


def _make_deal(db, lead):
    d = Deal(name="Project X", target_company="Acme",
             deal_type="lbo", deal_lead_id=lead.id, status="screening")
    db.add(d); db.flush()
    return d


def test_document_row_round_trip(db, make_user):
    u = make_user()
    deal = _make_deal(db, u)
    doc = Document(
        deal_id=deal.id, uploader_id=u.id,
        filename="CIM.pdf", storage_key="deals/x/docs/y/CIM.pdf",
        content_type="application/pdf", byte_size=1024,
        sha256="abc", source_kind="pdf_text",
    )
    db.add(doc); db.flush()
    fetched = db.execute(select(Document).where(Document.id == doc.id)).scalar_one()
    assert fetched.status == "pending"
    assert fetched.created_at is not None


def test_per_deal_sha256_unique_when_active(db, make_user):
    u = make_user()
    deal = _make_deal(db, u)
    db.add(Document(deal_id=deal.id, uploader_id=u.id,
                    filename="a.pdf", storage_key="k1",
                    content_type="application/pdf", byte_size=1,
                    sha256="dup", source_kind="pdf_text"))
    db.flush()
    db.add(Document(deal_id=deal.id, uploader_id=u.id,
                    filename="b.pdf", storage_key="k2",
                    content_type="application/pdf", byte_size=1,
                    sha256="dup", source_kind="pdf_text"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_chunk_embedding_column_accepts_vector(db, make_user):
    u = make_user()
    deal = _make_deal(db, u)
    doc = Document(deal_id=deal.id, uploader_id=u.id,
                   filename="a.pdf", storage_key="k", content_type="application/pdf",
                   byte_size=1, sha256="s", source_kind="pdf_text")
    db.add(doc); db.flush()
    from pallisade_core.settings import get_settings
    dim = get_settings().embed_dim
    chunk = DocumentChunk(
        document_id=doc.id, deal_id=deal.id, chunk_index=0,
        page_from=1, page_to=1, text="hello", token_count=1,
        embedding=[0.0] * dim,
    )
    db.add(chunk); db.flush()
    fetched = db.execute(select(DocumentChunk).where(DocumentChunk.id == chunk.id)).scalar_one()
    assert len(fetched.embedding) == dim
