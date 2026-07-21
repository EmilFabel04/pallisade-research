"""Tests for per-memo chat endpoints (GET/POST/DELETE + SSE messages).

Endpoints under /api/library/documents/{doc_id}/chat.
"""
from __future__ import annotations

import json

import pytest

from pallisade_core.library.models import LibraryDocument
from pallisade_core.runs.models import EvaluationRun


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_lib_doc(db, make_user, *, ticker: str = "NPN.JO",
                  kind: str = "final_trade_decision") -> LibraryDocument:
    owner = make_user()
    run = EvaluationRun(mode="public", user_id=owner.id, ticker=ticker, status="done")
    db.add(run)
    db.flush()
    doc = LibraryDocument(
        run_id=run.id,
        ticker=ticker,
        kind=kind,
        title=f"{ticker} — {kind}",
        body_md="Sample memo body.",
    )
    db.add(doc)
    db.flush()
    db.commit()
    return doc


def _build_client(client_for, me):
    from web.api.routers.chat import router as chat_router
    from web.api.deps import get_current_user
    client = client_for([("/api", chat_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: me
    return client


# ---------------------------------------------------------------------------
# Test 1 — GET creates conversation and returns empty history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lib_get_chat_creates_conversation(client_for, db, make_user):
    u = make_user()
    doc = _make_lib_doc(db, make_user)
    client = _build_client(client_for, u)

    r = await client.get(f"/api/library/documents/{doc.id}/chat")
    assert r.status_code == 200
    body = r.json()
    assert body["messages"] == []
    assert body["conversation_id"]


# ---------------------------------------------------------------------------
# Test 2 — POST /chat also creates the conversation (idempotent get-or-create)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lib_post_chat_creates_conversation(client_for, db, make_user):
    u = make_user()
    doc = _make_lib_doc(db, make_user)
    client = _build_client(client_for, u)

    r = await client.post(f"/api/library/documents/{doc.id}/chat")
    assert r.status_code == 201
    body = r.json()
    assert body["conversation_id"]

    # GET should return the same conversation
    r2 = await client.get(f"/api/library/documents/{doc.id}/chat")
    assert r2.json()["conversation_id"] == body["conversation_id"]


# ---------------------------------------------------------------------------
# Test 3 — POST /chat/messages streams tokens and persists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lib_post_message_streams_tokens_and_persists(
    client_for, db, make_user, monkeypatch
):
    from pallisade_core.rag import chat as chat_mod
    from pallisade_core.rag import retrieve as retrieve_mod
    from pallisade_core.rag.embeddings import FakeEmbedder

    u = make_user()
    doc = _make_lib_doc(db, make_user)

    monkeypatch.setattr(retrieve_mod, "build_default_embedder",
                        lambda: FakeEmbedder(dim=1024))

    class _StubChat:
        async def stream(self, *, system, messages):
            for t in ["Token1", " Token2"]:
                yield t

    monkeypatch.setattr(chat_mod, "AnthropicChatLLM", lambda **kw: _StubChat())

    client = _build_client(client_for, u)

    async with client.stream(
        "POST", f"/api/library/documents/{doc.id}/chat/messages",
        json={"content": "What is the outlook?"}
    ) as r:
        assert r.status_code == 200
        events = []
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))

    types = [e["type"] for e in events]
    assert types[0] == "token"
    assert "citations" in types
    assert types[-1] == "done"

    # Verify persistence via GET
    r2 = await client.get(f"/api/library/documents/{doc.id}/chat")
    msgs = r2.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["content"] == "Token1 Token2"


# ---------------------------------------------------------------------------
# Test 4 — DELETE resets the conversation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lib_delete_chat_resets(client_for, db, make_user, monkeypatch):
    from pallisade_core.rag import chat as chat_mod
    from pallisade_core.rag import retrieve as retrieve_mod
    from pallisade_core.rag.embeddings import FakeEmbedder

    u = make_user()
    doc = _make_lib_doc(db, make_user)

    monkeypatch.setattr(retrieve_mod, "build_default_embedder",
                        lambda: FakeEmbedder(dim=1024))

    class _StubChat:
        async def stream(self, *, system, messages):
            yield "hello"

    monkeypatch.setattr(chat_mod, "AnthropicChatLLM", lambda **kw: _StubChat())

    client = _build_client(client_for, u)

    # Post a message to populate conversation
    async with client.stream(
        "POST", f"/api/library/documents/{doc.id}/chat/messages",
        json={"content": "Seed message"},
    ) as r:
        assert r.status_code == 200
        async for _ in r.aiter_lines():
            pass

    # Verify messages exist
    r2 = await client.get(f"/api/library/documents/{doc.id}/chat")
    assert len(r2.json()["messages"]) > 0

    # Delete
    r3 = await client.delete(f"/api/library/documents/{doc.id}/chat")
    assert r3.status_code == 204

    # Verify empty
    r4 = await client.get(f"/api/library/documents/{doc.id}/chat")
    assert r4.json()["messages"] == []


# ---------------------------------------------------------------------------
# Test 5 — 404 on missing library document
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lib_get_chat_404_missing_doc(client_for, db, make_user):
    u = make_user()
    client = _build_client(client_for, u)

    import uuid
    r = await client.get(f"/api/library/documents/{uuid.uuid4()}/chat")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Test 6 — 404 when library doc is missing on messages endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_404_when_library_doc_missing(client_for, db, make_user):
    """The messages endpoint always returns 404 for any unknown doc_id.

    410 Gone is intentionally not used: the schema's ``chat_anchor_exclusive``
    CHECK constraint prevents ``library_doc_id`` from being NULL when
    ``kind='library_doc'``, making the ON DELETE SET NULL cascade unfireable and
    the orphaned-conversation state unreachable.  A missing doc is therefore
    always a 404, even if the user has prior library_doc conversations.
    """
    import uuid

    u = make_user()
    doc = _make_lib_doc(db, make_user)

    # Create a library_doc conversation for the user (anchored to doc) to ensure
    # the old 410 heuristic (user has any library_doc conv) would have fired.
    from pallisade_core.chat import service as chat_service
    from pallisade_core.chat.service import LibraryDocAnchor
    chat_service.get_or_create_conversation(
        db, user=u, anchor=LibraryDocAnchor(library_doc_id=doc.id)
    )
    db.commit()

    # POST to a completely different (non-existent) doc_id — must return 404.
    missing_id = uuid.uuid4()
    client = _build_client(client_for, u)
    r = await client.post(
        f"/api/library/documents/{missing_id}/chat/messages",
        json={"content": "This should 404"},
    )
    assert r.status_code == 404
