from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pallisade_core.db.base import Base

CONVICTIONS = ("bull", "bear", "watch")

# Built from CONVICTIONS so the constraint can't drift from the tuple above —
# renders identically to the literal migration 0024 already shipped:
# "conviction in ('bull','bear','watch')".
_CONVICTION_CHECK_SQL = "conviction in (" + ",".join(f"'{c}'" for c in CONVICTIONS) + ")"


class WatchlistItem(Base):
    """One ticker a user is tracking. Market data is never persisted here."""

    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_watchlist_items_user_ticker"),
        CheckConstraint(
            _CONVICTION_CHECK_SQL,
            name="watchlist_items_conviction_check",
        ),
        # Matches the index migration 0024 already creates; declared here too
        # so `alembic revision --autogenerate` doesn't propose dropping it.
        Index("ix_watchlist_items_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    conviction: Mapped[str] = mapped_column(String(16), nullable=False, server_default="watch")
    note: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
