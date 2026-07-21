from pallisade_core.documents import service as docs_service
from pallisade_core.documents.models import DocumentChunk
from pallisade_core.rag.embeddings import FakeEmbedder
from pallisade_core.rag.retrieve import retrieve_passages

from tests.pallisade.test_rag_retrieve import _seed_ready_doc


def _seed_second_doc(db, user, deal, *, texts=("banana", "blueberry")):
    """Seed a second ready document into an existing deal."""
    doc = docs_service.create_document(
        db, deal=deal, uploader=user,
        filename="y.pdf", content_type="application/pdf",
        data=deal.name.encode() + b"-second",
        source_kind="pdf_text",
    )
    db.flush()
    doc.status = "ready"
    fake = FakeEmbedder(dim=1024)
    vectors = fake.embed(list(texts), input_type="document")
    for i, (t, v) in enumerate(zip(texts, vectors)):
        db.add(DocumentChunk(
            document_id=doc.id, deal_id=deal.id, chunk_index=i,
            text=t, token_count=1, page_from=1, page_to=1, embedding=v,
        ))
    db.flush()
    return doc


def test_retrieve_passages_restricts_to_document_ids(db, make_user):
    u = make_user()
    deal, doc_a = _seed_ready_doc(db, u, deal_name="FilterDeal",
                                  texts=("apple", "apricot"))
    doc_b = _seed_second_doc(db, u, deal, texts=("banana", "blueberry"))

    fake = FakeEmbedder(dim=1024)
    out = retrieve_passages(db, deal_id=deal.id, query="apple",
                            k=10, document_ids=[doc_a.id], embedder=fake)

    assert len(out) > 0
    assert all(p.document_id == str(doc_a.id) for p in out)
    assert all(p.document_id != str(doc_b.id) for p in out)


def test_retrieve_passages_empty_document_ids_returns_nothing(db, make_user):
    u = make_user()
    deal, _ = _seed_ready_doc(db, u, deal_name="EmptyFilter",
                              texts=("cherry", "date"))

    fake = FakeEmbedder(dim=1024)
    result = retrieve_passages(db, deal_id=deal.id, query="cherry",
                               k=10, document_ids=[], embedder=fake)

    assert result == []
