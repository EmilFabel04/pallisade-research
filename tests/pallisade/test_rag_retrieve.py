from pallisade_core.deals.models import Deal
from pallisade_core.documents import service as docs_service
from pallisade_core.documents.models import DocumentChunk
from pallisade_core.rag.embeddings import FakeEmbedder
from pallisade_core.rag.retrieve import Passage, retrieve_passages


def _seed_ready_doc(db, user, *, deal_name="X", texts=("alpha", "beta", "gamma")):
    deal = Deal(name=deal_name, target_company="Y", deal_type="lbo",
                deal_lead_id=user.id, status="screening")
    db.add(deal); db.flush()
    doc = docs_service.create_document(db, deal=deal, uploader=user,
        filename="x.pdf", content_type="application/pdf",
        data=deal_name.encode() + b"-data",  # unique sha per deal
        source_kind="pdf_text")
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
    return deal, doc


def test_retrieve_passages_filters_to_deal(db, make_user):
    u = make_user()
    deal_a, _ = _seed_ready_doc(db, u, deal_name="A")
    deal_b, _ = _seed_ready_doc(db, u, deal_name="B", texts=("zulu", "yankee"))
    fake = FakeEmbedder(dim=1024)

    out = retrieve_passages(db, deal_id=deal_a.id, query="alpha",
                            k=5, embedder=fake)
    assert all(isinstance(p, Passage) for p in out)
    assert all(p.filename == "x.pdf" for p in out)
    # No deal-B chunks bled through:
    assert all(p.text in ("alpha", "beta", "gamma") for p in out)


def test_retrieve_ignores_deleted_or_unready(db, make_user):
    u = make_user()
    deal, doc = _seed_ready_doc(db, u, deal_name="C")
    fake = FakeEmbedder(dim=1024)
    doc.status = "embedding"
    db.flush()
    out = retrieve_passages(db, deal_id=deal.id, query="alpha", k=5, embedder=fake)
    assert out == []


def test_retrieve_orders_by_score_desc(db, make_user):
    u = make_user()
    deal, _ = _seed_ready_doc(db, u, deal_name="D")
    fake = FakeEmbedder(dim=1024)
    out = retrieve_passages(db, deal_id=deal.id, query="alpha",
                            k=3, embedder=fake)
    scores = [p.score for p in out]
    assert scores == sorted(scores, reverse=True)
