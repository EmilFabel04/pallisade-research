from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from pallisade_core.chat import service as chat_service
from pallisade_core.chat.service import GlobalAnchor, LibraryDocAnchor
from pallisade_core.deals import service as deals_service
from pallisade_core.library import service as lib_service
from pallisade_core.library.models import LibraryDocument
from pallisade_core.rag import chat as chat_mod
from pallisade_core.rag.chat import stream_answer, stream_answer_for_library
from pallisade_core.settings import get_settings
from pallisade_core.users.models import User
from sqlalchemy import func, select
from web.api.deps import get_current_user, get_db

router = APIRouter(tags=["chat"])


class PostMessageBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


def _load_deal(db: Session, deal_id: uuid.UUID, me: User):
    deal = deals_service.get_deal(db, deal_id)
    if deal is None or not deals_service.can_view(db, viewer=me, deal=deal):
        raise HTTPException(404, "deal not found")
    return deal


def _serialize_message(m) -> dict:
    return {
        "id": str(m.id), "role": m.role, "content": m.content,
        "citations": m.citations, "created_at": m.created_at.isoformat(),
    }


@router.get("/deals/{deal_id}/chat")
def get_chat(deal_id: uuid.UUID, db: Session = Depends(get_db),
             me: User = Depends(get_current_user)):
    deal = _load_deal(db, deal_id, me)
    conv = chat_service.get_or_create_conversation_for_deal(db, deal=deal, user=me)
    db.commit()
    msgs = chat_service.list_messages(db, conversation=conv)
    return {
        "conversation_id": str(conv.id),
        "title": conv.title,
        "messages": [_serialize_message(m) for m in msgs],
    }


@router.delete("/deals/{deal_id}/chat", status_code=204)
def reset_chat(deal_id: uuid.UUID, db: Session = Depends(get_db),
               me: User = Depends(get_current_user)):
    deal = _load_deal(db, deal_id, me)
    conv = chat_service.get_or_create_conversation_for_deal(db, deal=deal, user=me)
    chat_service.reset_conversation(db, conversation=conv)
    db.commit()
    return Response(status_code=204)


@router.post("/deals/{deal_id}/chat/messages")
def post_message(
    deal_id: uuid.UUID, body: PostMessageBody,
    db: Session = Depends(get_db), me: User = Depends(get_current_user),
):
    deal = _load_deal(db, deal_id, me)
    conv = chat_service.get_or_create_conversation_for_deal(db, deal=deal, user=me)
    history = [
        {"role": m.role, "content": m.content}
        for m in chat_service.list_messages(db, conversation=conv)
    ]
    user_msg = chat_service.append_message(db, conversation=conv, role="user",
                                            content=body.content)
    db.commit()

    settings = get_settings()
    chat_llm = chat_mod.AnthropicChatLLM(api_key=settings.anthropic_api_key,
                                         model=settings.chat_model)
    rewrite_llm = chat_mod.AnthropicRewriteLLM(api_key=settings.anthropic_api_key,
                                                model=settings.query_rewrite_model) if history else None

    async def _event_stream():
        assembled: list[str] = []
        citations: list[dict] = []
        try:
            async for ev in stream_answer(
                db, deal=deal, history=history, message=body.content,
                chat_llm=chat_llm, rewrite_llm=rewrite_llm,
            ):
                if ev["type"] == "token":
                    assembled.append(ev["text"])
                elif ev["type"] == "citations":
                    citations = ev["citations"]
                yield {"data": json.dumps(ev)}
        except Exception as exc:                       # noqa: BLE001
            # Emit an error event so the client knows the stream failed.
            yield {"data": json.dumps({"type": "error", "message": str(exc)})}
            # Roll back the orphaned user message so it doesn't pollute history.
            db.delete(user_msg)
            db.commit()
            raise
        # Persist assistant message after the stream completes.
        chat_service.append_message(
            db, conversation=conv, role="assistant",
            content="".join(assembled), citations=citations,
        )
        if conv.title is None and body.content:
            chat_service.set_title_if_missing(
                db, conversation=conv,
                title=body.content[:80],
            )
        db.commit()

    return EventSourceResponse(_event_stream())


# ---------------------------------------------------------------------------
# Library-doc chat endpoints
# ---------------------------------------------------------------------------

def _load_library_doc(db: Session, doc_id: uuid.UUID) -> LibraryDocument:
    """Return the LibraryDocument or raise 404.

    We always raise 404 (not 410 Gone) for a missing doc because the schema's
    ``chat_anchor_exclusive`` CHECK constraint prevents ``library_doc_id`` from
    being NULL when ``kind='library_doc'``, which makes the ``ON DELETE SET NULL``
    FK cascade effectively unfireable.  An orphaned conversation state can therefore
    never exist in practice, so there is no reachable trigger for 410.
    """
    doc = db.get(LibraryDocument, doc_id)
    if doc is None:
        raise HTTPException(404, "library document not found")
    return doc


@router.get("/library/documents/{doc_id}/chat")
def lib_get_chat(doc_id: uuid.UUID, db: Session = Depends(get_db),
                 me: User = Depends(get_current_user)):
    doc = _load_library_doc(db, doc_id)
    conv = chat_service.get_or_create_conversation(
        db, user=me, anchor=LibraryDocAnchor(library_doc_id=doc.id)
    )
    db.commit()
    msgs = chat_service.list_messages(db, conversation=conv)
    return {
        "conversation_id": str(conv.id),
        "title": conv.title,
        "messages": [_serialize_message(m) for m in msgs],
    }


@router.post("/library/documents/{doc_id}/chat", status_code=201)
def lib_create_chat(doc_id: uuid.UUID, db: Session = Depends(get_db),
                    me: User = Depends(get_current_user)):
    return lib_get_chat(doc_id, db, me)


@router.delete("/library/documents/{doc_id}/chat", status_code=204)
def lib_reset_chat(doc_id: uuid.UUID, db: Session = Depends(get_db),
                   me: User = Depends(get_current_user)):
    doc = _load_library_doc(db, doc_id)
    conv = chat_service.get_or_create_conversation(
        db, user=me, anchor=LibraryDocAnchor(library_doc_id=doc.id)
    )
    chat_service.reset_conversation(db, conversation=conv)
    db.commit()
    return Response(status_code=204)


@router.post("/library/documents/{doc_id}/chat/messages")
def lib_post_message(
    doc_id: uuid.UUID, body: PostMessageBody,
    db: Session = Depends(get_db), me: User = Depends(get_current_user),
):
    doc = _load_library_doc(db, doc_id)
    conv = chat_service.get_or_create_conversation(
        db, user=me, anchor=LibraryDocAnchor(library_doc_id=doc.id)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in chat_service.list_messages(db, conversation=conv)
    ]
    user_msg = chat_service.append_message(db, conversation=conv, role="user",  # noqa: F841
                                           content=body.content)
    db.commit()

    settings = get_settings()
    chat_llm = chat_mod.AnthropicChatLLM(api_key=settings.anthropic_api_key,
                                          model=settings.chat_model)

    async def _event_stream():
        assembled: list[str] = []
        citations: list[dict] = []
        try:
            async for ev in stream_answer_for_library(
                db, library_doc_id=doc.id, history=history,
                message=body.content, chat_llm=chat_llm,
            ):
                if ev["type"] == "token":
                    assembled.append(ev["text"])
                elif ev["type"] == "citations":
                    citations = ev["citations"]
                yield {"data": json.dumps(ev)}
        except Exception as exc:                       # noqa: BLE001
            # Emit error event and return — do not re-raise (matches deal-chat pattern).
            # The committed user message remains in history, same as deal-chat.
            yield {"data": json.dumps({"type": "error", "message": str(exc)})}
            return
        chat_service.append_message(
            db, conversation=conv, role="assistant",
            content="".join(assembled), citations=citations,
        )
        if conv.title is None and body.content:
            chat_service.set_title_if_missing(
                db, conversation=conv,
                title=body.content[:80],
            )
        db.commit()

    return EventSourceResponse(_event_stream())


# ---------------------------------------------------------------------------
# Global chat endpoints
# ---------------------------------------------------------------------------

@router.get("/chat/global")
def global_get_chat(db: Session = Depends(get_db),
                    me: User = Depends(get_current_user)):
    conv = chat_service.get_or_create_conversation(db, user=me, anchor=GlobalAnchor())
    db.commit()
    msgs = chat_service.list_messages(db, conversation=conv)
    return {
        "conversation_id": str(conv.id),
        "title": conv.title,
        "messages": [_serialize_message(m) for m in msgs],
    }


@router.post("/chat/global", status_code=201)
def global_create_chat(db: Session = Depends(get_db),
                       me: User = Depends(get_current_user)):
    return global_get_chat(db, me)


@router.delete("/chat/global", status_code=204)
def global_reset_chat(db: Session = Depends(get_db),
                      me: User = Depends(get_current_user)):
    conv = chat_service.get_or_create_conversation(db, user=me, anchor=GlobalAnchor())
    chat_service.reset_conversation(db, conversation=conv)
    db.commit()
    return Response(status_code=204)


@router.post("/chat/global/messages")
def global_post_message(
    body: PostMessageBody,
    db: Session = Depends(get_db), me: User = Depends(get_current_user),
):
    conv = chat_service.get_or_create_conversation(db, user=me, anchor=GlobalAnchor())
    history = [
        {"role": m.role, "content": m.content}
        for m in chat_service.list_messages(db, conversation=conv)
    ]

    # Empty-library guard: skip LLM, emit canned polite message.
    # Must run BEFORE persisting the user message so the turn is not stored.
    if db.scalar(select(func.count(LibraryDocument.id))) == 0:
        async def _empty_gen():
            yield {"data": json.dumps({"type": "token", "text": "No memos in the library yet."})}
            yield {"data": json.dumps({"type": "citations", "citations": []})}
            yield {"data": json.dumps({"type": "done"})}
        return EventSourceResponse(_empty_gen())

    chat_service.append_message(db, conversation=conv, role="user", content=body.content)
    db.commit()

    titles = lib_service.parse_mentions(body.content)
    mentioned = lib_service.resolve_mentions(db, titles)
    mentioned_ids = [m.id for m in mentioned]

    settings = get_settings()
    chat_llm = chat_mod.AnthropicChatLLM(api_key=settings.anthropic_api_key,
                                          model=settings.chat_model)

    async def _global_event_stream():
        assembled: list[str] = []
        citations: list[dict] = []
        try:
            async for ev in stream_answer_for_library(
                db, library_doc_id=None, mentioned_doc_ids=mentioned_ids,
                history=history, message=body.content, chat_llm=chat_llm,
            ):
                if ev["type"] == "token":
                    assembled.append(ev["text"])
                elif ev["type"] == "citations":
                    citations = ev["citations"]
                yield {"data": json.dumps(ev)}
        except Exception as exc:                       # noqa: BLE001
            # Emit error event and return — do not re-raise (matches lib-chat pattern).
            yield {"data": json.dumps({"type": "error", "message": str(exc)})}
            return
        chat_service.append_message(
            db, conversation=conv, role="assistant",
            content="".join(assembled), citations=citations,
        )
        if conv.title is None and body.content:
            chat_service.set_title_if_missing(
                db, conversation=conv,
                title=body.content[:80],
            )
        db.commit()

    return EventSourceResponse(_global_event_stream())
