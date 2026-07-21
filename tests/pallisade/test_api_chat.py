import json

import pytest

from pallisade_core.deals.models import Deal


@pytest.mark.asyncio
async def test_get_chat_creates_conversation_returns_empty_history(client_for, db, make_user):
    u = make_user()
    d = Deal(name="X", target_company="Y", deal_type="lbo",
             deal_lead_id=u.id, status="screening")
    db.add(d); db.flush(); db.commit()

    from web.api.routers.chat import router as chat_router
    from web.api.deps import get_current_user
    client = client_for([("/api", chat_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    r = await client.get(f"/api/deals/{d.id}/chat")
    assert r.status_code == 200
    body = r.json()
    assert body["messages"] == []
    assert body["conversation_id"]


@pytest.mark.asyncio
async def test_post_message_streams_tokens_and_persists(client_for, db, make_user, monkeypatch):
    from pallisade_core.documents import service as ds
    from pallisade_core.documents.models import DocumentChunk
    from pallisade_core.rag import chat as chat_mod
    from pallisade_core.rag import retrieve as retrieve_mod
    from pallisade_core.rag.embeddings import FakeEmbedder

    u = make_user()
    d = Deal(name="X", target_company="Y", deal_type="lbo",
             deal_lead_id=u.id, status="screening")
    db.add(d); db.flush()
    doc = ds.create_document(db, deal=d, uploader=u, filename="x.pdf",
        content_type="application/pdf", data=b"x", source_kind="pdf_text")
    db.flush()
    doc.status = "ready"
    vec = FakeEmbedder(dim=1024).embed(["alpha"], input_type="document")[0]
    db.add(DocumentChunk(document_id=doc.id, deal_id=d.id, chunk_index=0,
                         text="alpha", token_count=1, page_from=1, page_to=1,
                         embedding=vec))
    db.flush(); db.commit()

    monkeypatch.setattr(retrieve_mod, "build_default_embedder",
                        lambda: FakeEmbedder(dim=1024))

    class _StubChat:
        async def stream(self, *, system, messages):
            for t in ["Hi", " there"]:
                yield t

    monkeypatch.setattr(chat_mod, "AnthropicChatLLM",
                        lambda **kw: _StubChat())
    monkeypatch.setattr(chat_mod, "AnthropicRewriteLLM",
                        lambda **kw: None)

    from web.api.routers.chat import router as chat_router
    from web.api.deps import get_current_user
    client = client_for([("/api", chat_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    async with client.stream("POST", f"/api/deals/{d.id}/chat/messages",
                             json={"content": "explain alpha"}) as r:
        assert r.status_code == 200
        events = []
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))

    types = [e["type"] for e in events]
    assert types[0] == "token"
    assert "citations" in types
    assert types[-1] == "done"

    # Round-trip via GET should now include both user and assistant messages.
    r2 = await client.get(f"/api/deals/{d.id}/chat")
    msgs = r2.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["content"] == "Hi there"


@pytest.mark.asyncio
async def test_delete_chat_clears_messages(client_for, db, make_user):
    from pallisade_core.chat import service as chat_service
    u = make_user()
    d = Deal(name="X", target_company="Y", deal_type="lbo",
             deal_lead_id=u.id, status="screening")
    db.add(d); db.flush()
    conv = chat_service.get_or_create_conversation_for_deal(db, deal=d, user=u)
    chat_service.append_message(db, conversation=conv, role="user", content="x")
    db.commit()

    from web.api.routers.chat import router as chat_router
    from web.api.deps import get_current_user
    client = client_for([("/api", chat_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    r = await client.delete(f"/api/deals/{d.id}/chat")
    assert r.status_code == 204
    r2 = await client.get(f"/api/deals/{d.id}/chat")
    assert r2.json()["messages"] == []


@pytest.mark.asyncio
async def test_chat_404_for_non_team_member(client_for, db, make_user):
    u = make_user()
    intruder = make_user()
    d = Deal(name="X", target_company="Y", deal_type="lbo",
             deal_lead_id=u.id, status="screening")
    db.add(d); db.flush(); db.commit()

    from web.api.routers.chat import router as chat_router
    from web.api.deps import get_current_user
    client = client_for([("/api", chat_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: intruder

    r = await client.get(f"/api/deals/{d.id}/chat")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_post_message_stream_failure_rolls_back_user_message(client_for, db, make_user, monkeypatch):
    from pallisade_core.documents import service as ds
    from pallisade_core.documents.models import DocumentChunk
    from pallisade_core.rag import chat as chat_mod
    from pallisade_core.rag import retrieve as retrieve_mod
    from pallisade_core.rag.embeddings import FakeEmbedder

    u = make_user()
    d = Deal(name="X", target_company="Y", deal_type="lbo",
             deal_lead_id=u.id, status="screening")
    db.add(d); db.flush()
    doc = ds.create_document(db, deal=d, uploader=u, filename="x.pdf",
        content_type="application/pdf", data=b"x", source_kind="pdf_text")
    db.flush()
    doc.status = "ready"
    vec = FakeEmbedder(dim=1024).embed(["alpha"], input_type="document")[0]
    db.add(DocumentChunk(document_id=doc.id, deal_id=d.id, chunk_index=0,
                         text="alpha", token_count=1, page_from=1, page_to=1,
                         embedding=vec))
    db.flush(); db.commit()

    monkeypatch.setattr(retrieve_mod, "build_default_embedder",
                        lambda: FakeEmbedder(dim=1024))

    class _BrokenChat:
        async def stream(self, *, system, messages):
            yield "Hello"  # partial token before failure
            raise RuntimeError("simulated upstream failure")

    monkeypatch.setattr(chat_mod, "AnthropicChatLLM",
                        lambda **kw: _BrokenChat())
    monkeypatch.setattr(chat_mod, "AnthropicRewriteLLM",
                        lambda **kw: None)

    from web.api.routers.chat import router as chat_router
    from web.api.deps import get_current_user
    client = client_for([("/api", chat_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    # Stream and ignore the body — we just want the side-effect on persistence.
    try:
        async with client.stream("POST", f"/api/deals/{d.id}/chat/messages",
                                 json={"content": "broken request"}) as r:
            async for _ in r.aiter_lines():
                pass
    except Exception:
        pass

    # GET chat — the orphaned user message must NOT be there.
    r2 = await client.get(f"/api/deals/{d.id}/chat")
    msgs = r2.json()["messages"]
    contents = [m["content"] for m in msgs]
    assert "broken request" not in contents
