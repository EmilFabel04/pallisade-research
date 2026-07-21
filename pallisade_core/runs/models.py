from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pallisade_core.db.base import Base
# Ensure FK target tables are registered with the SQLAlchemy metadata.
from pallisade_core.deals.models import Deal  # noqa: F401
from pallisade_core.users.models import User  # noqa: F401


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint("mode in ('public','private')", name="runs_mode_check"),
        CheckConstraint(
            "status in ('queued','running','done','failed')", name="runs_status_check"
        ),
        CheckConstraint(
            "(mode = 'public' and ticker is not null and deal_id is null) "
            "or (mode = 'private' and deal_id is not null)",
            name="runs_mode_consistency_check",
        ),
        Index("ix_runs_user_created", "user_id", "created_at"),
        Index("ix_runs_deal_created", "deal_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    mode: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id")
    )
    ticker: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="queued")
    artifacts_root_key: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    thesis: Mapped[str | None] = mapped_column(Text)
    params: Mapped[dict | None] = mapped_column(JSONB)
    reports: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    result: Mapped[dict | None] = mapped_column(JSONB)
    current_node: Mapped[str | None] = mapped_column(String)
