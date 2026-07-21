"""Durable, append-only per-run event log — the transport for live debate streaming.

The worker appends; the SSE endpoint tails from a cursor. The rows ARE the
history, so live streaming and reopen-replay are the same query (spec §D2/§D3).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Index, Integer, String,
    UniqueConstraint, func, select, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from pallisade_core.db.base import Base
# Ensure the FK target is registered with the SQLAlchemy metadata.
from pallisade_core.runs.models import EvaluationRun  # noqa: F401


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "seq", name="uq_run_events_run_seq"),
        Index("ix_run_events_run_seq", "run_id", "seq"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


def append_event(session: Session, *, run_id, seq: int, type: str, payload: dict) -> RunEvent:
    row = RunEvent(run_id=run_id, seq=seq, type=type, payload=payload or {})
    session.add(row)
    return row


def max_seq(session: Session, *, run_id) -> int:
    return session.scalar(
        select(func.coalesce(func.max(RunEvent.seq), 0)).where(RunEvent.run_id == run_id)
    ) or 0


def list_events(
    session: Session, *, run_id, after_seq: int = 0, limit: int = 500
) -> list[RunEvent]:
    """Events with seq strictly greater than *after_seq*, oldest first.

    Cursor contract (spec §6.1): seq starts at 1, so after_seq=0 replays
    everything. Never relax `>` to `>=` — that re-delivers the last-seen event
    on every reconnect.
    """
    stmt = (
        select(RunEvent)
        .where(RunEvent.run_id == run_id, RunEvent.seq > after_seq)
        .order_by(RunEvent.seq)
        .limit(limit)
    )
    return list(session.execute(stmt).scalars().all())


class RunEventEmitter:
    """Appends events, each in its OWN committed session.

    Spec §5.2: the worker's handler session is only committed after the handler
    returns. If events rode on that session nothing would reach the SSE reader
    until the debate finished — the whole feature would silently degrade to an
    end-of-run dump. Taking a *factory* rather than a session makes that bug
    hard to write.
    """

    def __init__(self, *, run_id: uuid.UUID, session_factory: Callable[[], Any]) -> None:
        self._run_id = run_id
        self._sf = session_factory
        self._seq: int | None = None

    def _next_seq(self) -> int:
        if self._seq is None:
            with self._sf() as s:
                self._seq = max_seq(s, run_id=self._run_id)
        self._seq += 1
        return self._seq

    def emit(self, type: str, payload: dict) -> int:
        seq = self._next_seq()
        with self._sf() as s:
            append_event(s, run_id=self._run_id, seq=seq, type=type, payload=payload)
            s.commit()
        return seq
