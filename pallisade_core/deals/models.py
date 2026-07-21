from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pallisade_core.db.base import Base


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("deal_type in ('lbo','growth','private_credit')", name="deals_type_check"),
        CheckConstraint(
            "status in ('screening','loi','dd','ic','closed_won','closed_lost')",
            name="deals_status_check",
        ),
        Index("ix_deals_deal_lead_id", "deal_lead_id"),
        Index("ix_deals_status", "status"),
        Index("ix_deals_deleted_at", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_company: Mapped[str] = mapped_column(String, nullable=False)
    deal_type: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="screening")
    description: Mapped[str | None] = mapped_column(String)
    check_size_usd: Mapped[int | None] = mapped_column(BigInteger)
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    deal_lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )


class DealTeamMember(Base):
    __tablename__ = "deal_team_members"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
