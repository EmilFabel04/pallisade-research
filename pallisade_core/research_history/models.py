from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pallisade_core.db.base import Base
# Ensure the FK target table is registered with the SQLAlchemy metadata.
from pallisade_core.users.models import User  # noqa: F401


class ResearchConversation(Base):
    """A saved research-copilot conversation (all turns, with cited dossiers).

    `payload` holds the full ordered message list exactly as the UI renders it —
    each assistant turn carries its CitedAnswer — so reopening restores narration
    and dossier. Strictly user-scoped.
    """

    __tablename__ = "research_conversations"
    __table_args__ = (
        Index("ix_research_conversations_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
