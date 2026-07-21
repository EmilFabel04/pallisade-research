from __future__ import annotations

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from pallisade_core.research_history.models import ResearchConversation


def upsert_conversation(
    session: Session,
    *,
    user,
    conversation_id,
    title: str,
    messages: list,
) -> ResearchConversation:
    """Create a conversation, or update it when `conversation_id` names one the
    user owns. An id that is unknown or owned by someone else falls through to a
    fresh create — a user can never write into another user's conversation.
    """
    if conversation_id is not None:
        existing = session.execute(
            select(ResearchConversation).where(
                ResearchConversation.id == conversation_id,
                ResearchConversation.user_id == user.id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.title = title
            existing.payload = messages
            session.flush()
            return existing

    row = ResearchConversation(user_id=user.id, title=title, payload=messages)
    session.add(row)
    session.flush()
    return row


def list_conversations(session: Session, *, user) -> list[ResearchConversation]:
    return list(
        session.execute(
            select(ResearchConversation)
            .where(ResearchConversation.user_id == user.id)
            .order_by(desc(ResearchConversation.updated_at))
        ).scalars()
    )


def get_conversation(session: Session, *, user, conversation_id) -> ResearchConversation | None:
    return session.execute(
        select(ResearchConversation).where(
            ResearchConversation.id == conversation_id,
            ResearchConversation.user_id == user.id,
        )
    ).scalar_one_or_none()


def delete_conversation(session: Session, *, user, conversation_id) -> bool:
    result = session.execute(
        delete(ResearchConversation).where(
            ResearchConversation.id == conversation_id,
            ResearchConversation.user_id == user.id,
        )
    )
    return result.rowcount > 0
