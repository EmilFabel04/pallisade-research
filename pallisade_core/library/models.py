from __future__ import annotations

import os as _os
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pallisade_core.db.base import Base
# Ensure FK target tables are registered with the SQLAlchemy metadata.
from pallisade_core.runs.models import EvaluationRun  # noqa: F401

# Read embed_dim at import time from env; mirrors Settings.embed_dim default of 1024.
# We do NOT call get_settings() here to avoid requiring all env vars to be present
# at module-load time (which would break pytest collection before the _env fixture runs).
_EMBED_DIM: int = int(_os.environ.get("PALLISADE_EMBED_DIM", "1024"))


LIBRARY_KINDS = (
    "market_report", "sentiment_report", "news_report", "fundamentals_report",
    "investment_plan", "trader_investment_plan", "final_trade_decision",
)


class LibraryDocument(Base):
    __tablename__ = "library_documents"
    __table_args__ = (
        CheckConstraint(
            "kind in ('market_report','sentiment_report','news_report',"
            "'fundamentals_report','investment_plan','trader_investment_plan',"
            "'final_trade_decision')",
            name="library_documents_kind_check",
        ),
        UniqueConstraint("run_id", "kind", name="uq_library_run_kind"),
        Index("ix_library_ticker_created", "ticker", "created_at"),
        Index("ix_library_kind_created", "kind", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LibraryChunk(Base):
    __tablename__ = "library_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    library_doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(_EMBED_DIM))
