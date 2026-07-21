import pytest
from pallisade_connections.models import default_org_id
from pallisade_core.documents import service as docs_service
from pallisade_core.documents.models import DocumentChunk
from pallisade_core.rag.embeddings import FakeEmbedder
from pallisade_core.rag.retrieve import retrieve_passages


def _seed_org_doc(db, user, org_id, texts):
    doc = docs_service.create_org_document(
        db, org_id=org_id, uploader=user, filename="m.xlsx",
        content_type="application/octet-stream",
        data=("".join(texts)).encode() + b"-org", source_kind="xlsx",
    )
    db.flush()
    doc.status = "ready"
    fake = FakeEmbedder(dim=1024)
    for i, (t, v) in enumerate(zip(texts, fake.embed(list(texts), input_type="document"))):
        db.add(DocumentChunk(
            document_id=doc.id, org_id=org_id, deal_id=None, chunk_index=i,
            text=t, token_count=1, sheet_name="Model", embedding=v,
        ))
    db.flush()
    return doc


def test_retrieve_by_org_returns_org_chunks(db, make_user):
    user = make_user()
    org_id = default_org_id(db)
    _seed_org_doc(db, user, org_id, texts=("Revenue: R42.1bn", "EBITDA: R9bn"))

    out = retrieve_passages(db, org_id=org_id, query="Revenue",
                            k=10, embedder=FakeEmbedder(dim=1024))
    assert len(out) > 0
    assert any("42.1bn" in p.text for p in out)


def test_retrieve_requires_a_corpus(db):
    with pytest.raises(ValueError):
        retrieve_passages(db, query="x", embedder=FakeEmbedder(dim=1024))
