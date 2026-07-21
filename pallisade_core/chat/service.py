from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Union

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pallisade_core.chat.models import ChatConversation, ChatMessage
from pallisade_core.deals.models import Deal
from pallisade_core.users.models import User


# ---------------------------------------------------------------------------
# Typed anchor discriminators
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DealAnchor:
    deal_id: uuid.UUID


@dataclass(frozen=True)
class LibraryDocAnchor:
    library_doc_id: uuid.UUID


@dataclass(frozen=True)
class GlobalAnchor:
    pass


Anchor = Union[DealAnchor, LibraryDocAnchor, GlobalAnchor]


# ---------------------------------------------------------------------------
# Conversation get-or-create (polymorphic, keyed on anchor)
# ---------------------------------------------------------------------------

def get_or_create_conversation(
    db: Session, *, user: User, anchor: Anchor
) -> ChatConversation:
    if isinstance(anchor, DealAnchor):
        stmt = select(ChatConversation).where(
            ChatConversation.kind == "deal",
            ChatConversation.deal_id == anchor.deal_id,
            ChatConversation.user_id == user.id,
        )
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing
        conv = ChatConversation(
            kind="deal", deal_id=anchor.deal_id, user_id=user.id,
        )
    elif isinstance(anchor, LibraryDocAnchor):
        stmt = select(ChatConversation).where(
            ChatConversation.kind == "library_doc",
            ChatConversation.library_doc_id == anchor.library_doc_id,
            ChatConversation.user_id == user.id,
        )
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing
        conv = ChatConversation(
            kind="library_doc",
            library_doc_id=anchor.library_doc_id,
            user_id=user.id,
        )
    elif isinstance(anchor, GlobalAnchor):
        stmt = select(ChatConversation).where(
            ChatConversation.kind == "global",
            ChatConversation.user_id == user.id,
        )
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing
        conv = ChatConversation(kind="global", user_id=user.id)
    else:
        raise TypeError(f"unknown anchor type: {type(anchor)!r}")

    db.add(conv)
    db.flush()
    return conv


# ---------------------------------------------------------------------------
# Thin shim for existing deal-based callers
# ---------------------------------------------------------------------------

def get_or_create_conversation_for_deal(
    db: Session, *, deal: Deal, user: User
) -> ChatConversation:
    return get_or_create_conversation(
        db, user=user, anchor=DealAnchor(deal_id=deal.id)
    )


# ---------------------------------------------------------------------------
# Message helpers (unchanged)
# ---------------------------------------------------------------------------

def append_message(
    session: Session, *, conversation: ChatConversation, role: str, content: str,
    citations: list[dict] | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        conversation_id=conversation.id, role=role, content=content,
        citations=citations,
    )
    session.add(msg)
    session.flush()
    return msg


def list_messages(session: Session, *, conversation: ChatConversation) -> list[ChatMessage]:
    return list(session.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.ordinal)
    ).scalars())


def reset_conversation(session: Session, *, conversation: ChatConversation) -> None:
    session.execute(
        delete(ChatMessage).where(ChatMessage.conversation_id == conversation.id)
    )
    conversation.title = None
    session.flush()


def set_title_if_missing(session: Session, *, conversation: ChatConversation, title: str) -> None:
    if conversation.title is None:
        conversation.title = title
        session.flush()
