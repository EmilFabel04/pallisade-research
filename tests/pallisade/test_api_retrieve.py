import pytest

from pallisade_core.deals.models import Deal


@pytest.mark.asyncio
async def test_retrieve_endpoint_returns_passages(client_for, db, make_user, monkeypatch):
    u = make_user()
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=u.id, status="screening")
    db.add(deal); db.flush()

    # Stub the embedder used by the router to FakeEmbedder.
    from pallisade_core.rag import retrieve as retrieve_mod
    from pallisade_core.rag.embeddings import FakeEmbedder
    monkeypatch.setattr(retrieve_mod, "build_default_embedder",
                        lambda: FakeEmbedder(dim=1024))

    # Seed a ready doc with one chunk.
    from pallisade_core.documents import service as ds
    from pallisade_core.documents.models import DocumentChunk
    doc = ds.create_document(db, deal=deal, uploader=u,
        filename="x.pdf", content_type="application/pdf",
        data=b"xx", source_kind="pdf_text")
    db.flush()
    doc.status = "ready"
    vec = FakeEmbedder(dim=1024).embed(["alpha"], input_type="document")[0]
    db.add(DocumentChunk(document_id=doc.id, deal_id=deal.id, chunk_index=0,
                         text="alpha", token_count=1, page_from=1, page_to=1,
                         embedding=vec))
    db.flush()
    db.commit()

    from web.api.routers.retrieve import router as retrieve_router
    from web.api.deps import get_current_user
    client = client_for([("/api", retrieve_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    r = await client.post(f"/api/deals/{deal.id}/retrieve",
                          json={"query": "alpha", "k": 5})
    assert r.status_code == 200
    body = r.json()
    assert len(body["passages"]) == 1
    p = body["passages"][0]
    assert p["text"] == "alpha"
    assert p["filename"] == "x.pdf"
    assert p["page_from"] == 1


@pytest.mark.asyncio
async def test_retrieve_endpoint_returns_404_for_non_team_member(client_for, db, make_user):
    u = make_user()
    intruder = make_user()
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=u.id, status="screening")
    db.add(deal); db.flush(); db.commit()

    from web.api.routers.retrieve import router as retrieve_router
    from web.api.deps import get_current_user
    client = client_for([("/api", retrieve_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: intruder

    r = await client.post(f"/api/deals/{deal.id}/retrieve",
                          json={"query": "x"})
    assert r.status_code == 404
