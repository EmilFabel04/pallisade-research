"""Tests for the global chat endpoints at /api/chat/global."""
from __future__ import annotations

import json

import pytest

from pallisade_core.library.models import LibraryDocument
from pallisade_core.runs.models import EvaluationRun


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_client(client_for, me):
    from web.api.routers.chat import router as chat_router
    from web.api.deps import get_current_user
    client = client_for([("/api", chat_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: me
    return client


def _make_lib_doc(db, make_user, *, ticker: str = "NPN.JO",
                  kind: str = "final_trade_decision",
                  title: str | None = None) -> LibraryDocument:
    owner = make_user()
    run = EvaluationRun(mode="public", user_id=owner.id, ticker=ticker, status="done")
    db.add(run)
    db.flush()
    doc = LibraryDocument(
        run_id=run.id,
        ticker=ticker,
        kind=kind,
        title=title or f"{ticker} — {kind}",
        body_md="Sample memo body for global chat tests.",
    )
    db.add(doc)
    db.flush()
    db.commit()
    return doc


# ---------------------------------------------------------------------------
# Test 1 — GET /api/chat/global twice returns the same conversation_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_global_chat_is_singleton_per_user(client_for, db, make_user):
    u = make_user()
    client = _build_client(client_for, u)

    r1 = await client.get("/api/chat/global")
    assert r1.status_code == 200
    conv_id_1 = r1.json()["conversation_id"]

    r2 = await client.get("/api/chat/global")
    assert r2.status_code == 200
    conv_id_2 = r2.json()["conversation_id"]

    assert conv_id_1 == conv_id_2


# ---------------------------------------------------------------------------
# Test 2 — POST to empty library returns polite canned message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_global_chat_empty_library_polite_message(client_for, db, make_user):
    u = make_user()
    client = _build_client(client_for, u)

    async with client.stream(
        "POST", "/api/chat/global/messages",
        json={"content": "Tell me about the memos."},
    ) as r:
        assert r.status_code == 200
        events = []
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))

    # Find all token texts
    token_texts = [e["text"] for e in events if e.get("type") == "token"]
    full_text = "".join(token_texts)
    assert "No memos in the library yet" in full_text

    # Also confirm done event is present
    types = [e["type"] for e in events]
    assert "done" in types

    # The user message must NOT have been persisted — history should be empty.
    r_history = await client.get("/api/chat/global")
    assert r_history.status_code == 200
    assert r_history.json()["messages"] == [], (
        "User message should not be persisted when the empty-library guard fires"
    )


# ---------------------------------------------------------------------------
# Test 3 — @mention is resolved and passed to retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mention_resolves_to_library_doc(client_for, db, make_user, monkeypatch):
    from pallisade_core.rag import chat as chat_mod
    from pallisade_core.rag import retrieve as retrieve_mod
    from pallisade_core.rag.embeddings import FakeEmbedder

    u = make_user()
    doc = _make_lib_doc(db, make_user, ticker="NPN.JO",
                        title="NPN memo — final_trade_decision — 2026-05-27")

    monkeypatch.setattr(retrieve_mod, "build_default_embedder",
                        lambda: FakeEmbedder(dim=1024))

    # Capture mentioned_doc_ids passed to retrieve_for_global.
    # chat.py imports retrieve_for_global directly into its own namespace, so
    # we must patch the name on the chat module, not on retrieve_mod.
    captured_mentioned_ids: list = []
    _real_retrieve = retrieve_mod.retrieve_for_global

    def _patched_retrieve_for_global(db_, *, query, k, mentioned_doc_ids=None):
        if mentioned_doc_ids is not None:
            captured_mentioned_ids.extend(mentioned_doc_ids)
        return _real_retrieve(db_, query=query, k=k, mentioned_doc_ids=mentioned_doc_ids)

    monkeypatch.setattr(chat_mod, "retrieve_for_global", _patched_retrieve_for_global)

    # Also stub the LLM so we don't hit the real API
    class _StubChat:
        async def stream(self, *, system, messages):
            yield "stub answer"

    monkeypatch.setattr(chat_mod, "AnthropicChatLLM", lambda **kw: _StubChat())

    client = _build_client(client_for, u)

    async with client.stream(
        "POST", "/api/chat/global/messages",
        json={"content": '@"NPN memo" what is the alpha?'},
    ) as r:
        assert r.status_code == 200
        async for _ in r.aiter_lines():
            pass

    # The doc.id should have been included in the mentioned_doc_ids passed to retrieval
    assert doc.id in captured_mentioned_ids
