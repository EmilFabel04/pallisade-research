import pytest

from pallisade_core.chat.models import ChatConversation, ChatMessage
from pallisade_core.deals.models import Deal
from pallisade_core.rag.chat import (
    ChatLLM, RewriteLLM, build_user_prompt, build_system_prompt, stream_answer,
)
from pallisade_core.rag.retrieve import Passage


class _FakeChatLLM:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.last_system = None
        self.last_messages = None

    async def stream(self, *, system: str, messages: list[dict]):
        self.last_system = system
        self.last_messages = messages
        for t in self.tokens:
            yield t


class _FakeRewriteLLM:
    def __init__(self, queries: list[str]):
        self.queries = queries
    async def rewrite(self, *, history: list[dict], message: str) -> list[str]:
        return self.queries


def test_build_system_prompt_contains_deal_metadata_and_citation_rule(db, make_user):
    u = make_user()
    deal = Deal(name="Falcon", target_company="Acme",
                deal_type="lbo", deal_lead_id=u.id, status="screening")
    db.add(deal); db.flush()
    sys_prompt = build_system_prompt(deal=deal)
    assert "Falcon" in sys_prompt
    assert "Acme" in sys_prompt
    assert "[filename p.PAGE]" in sys_prompt


def test_build_user_prompt_includes_passages_with_labels():
    passages = [
        Passage(chunk_id="1", document_id="d1", filename="CIM.pdf",
                page_from=42, page_to=42, sheet_name=None,
                text="EBITDA 24.5%", score=0.9),
        Passage(chunk_id="2", document_id="d2", filename="Model.xlsx",
                page_from=None, page_to=None, sheet_name="Assumptions",
                text="Revenue grows", score=0.7),
    ]
    prompt = build_user_prompt(history=[], passages=passages, message="What is EBITDA?")
    assert "[CIM.pdf p.42]" in prompt
    assert "[Model.xlsx · Assumptions]" in prompt
    assert "What is EBITDA?" in prompt


@pytest.mark.asyncio
async def test_stream_answer_yields_tokens_then_citations_then_done(db, make_user, monkeypatch):
    from pallisade_core.documents import service as ds
    from pallisade_core.documents.models import DocumentChunk
    from pallisade_core.rag import retrieve as retrieve_mod
    from pallisade_core.rag.embeddings import FakeEmbedder

    u = make_user()
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=u.id, status="screening")
    db.add(deal); db.flush()
    doc = ds.create_document(db, deal=deal, uploader=u, filename="x.pdf",
        content_type="application/pdf", data=b"x", source_kind="pdf_text")
    db.flush()
    doc.status = "ready"
    vec = FakeEmbedder(dim=1024).embed(["alpha"], input_type="document")[0]
    db.add(DocumentChunk(document_id=doc.id, deal_id=deal.id, chunk_index=0,
                         text="alpha", token_count=1, page_from=1, page_to=1,
                         embedding=vec))
    db.flush()

    monkeypatch.setattr(retrieve_mod, "build_default_embedder",
                        lambda: FakeEmbedder(dim=1024))

    chat = _FakeChatLLM(tokens=["Hello", " world", "."])
    rew = _FakeRewriteLLM(queries=["alpha"])

    events = []
    async for ev in stream_answer(
        db, deal=deal, history=[], message="explain alpha",
        chat_llm=chat, rewrite_llm=rew,
    ):
        events.append(ev)

    types = [e["type"] for e in events]
    assert types[:3] == ["token", "token", "token"]
    assert types[-2] == "citations"
    assert types[-1] == "done"
    cites = events[-2]["citations"]
    assert cites[0]["filename"] == "x.pdf"
