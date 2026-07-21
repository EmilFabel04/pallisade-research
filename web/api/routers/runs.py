from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from pallisade_core.db.session import get_session_factory
from pallisade_core.runs import events as events_service
from pallisade_core.runs import service as runs_service
from pallisade_core.users.models import User
from web.api.deps import get_current_user, get_db

POLL_SECONDS = 0.5
KEEPALIVE_SECONDS = 15.0
TERMINAL = {"done", "failed"}


class NewRunBody(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    trade_date: str = Field(..., description="YYYY-MM-DD")
    analysts: list[str] = Field(
        default_factory=lambda: ["market", "social", "news", "fundamentals"]
    )
    asset_type: str = Field(default="stock")
    llm_provider: str | None = None
    deep_think_llm: str | None = None
    quick_think_llm: str | None = None
    max_debate_rounds: int | None = None
    analysts_only: bool = False


router = APIRouter(tags=["runs"])


@router.post("/runs")
def create_run(
    body: NewRunBody,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """Enqueue a durable debate. Executes nothing — the worker owns execution."""
    row = runs_service.create_public_run(
        db, user=me, ticker=body.ticker,
        params={
            "trade_date": body.trade_date,
            "asset_type": body.asset_type,
            "analysts": body.analysts,
            "llm_provider": body.llm_provider,
            "deep_think_llm": body.deep_think_llm,
            "quick_think_llm": body.quick_think_llm,
            "max_debate_rounds": body.max_debate_rounds,
            "analysts_only": body.analysts_only,
            "org_id": str(me.org_id) if me.org_id else None,
        },
    )
    db.flush()
    runs_service.create_public_run_job(db, run=row)
    db.commit()
    db.refresh(row)
    kind = "analysts" if body.analysts_only else "debate"
    runs_service.prune_runs(db, user=me, kind=kind, keep=5)
    db.commit()
    return {"run_id": str(row.id)}


@router.get("/runs")
def list_runs(
    kind: str | None = None,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    limit = 5 if kind in ("analysts", "debate") else None
    rows = runs_service.list_for_user(db, user=me, kind=kind, limit=limit)
    return {
        "runs": [
            {
                "id": str(r.id),
                "ticker": r.ticker,
                "trade_date": (r.params or {}).get("trade_date"),
                "analysts": (r.params or {}).get("analysts"),
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


def _require_owned(db: Session, run_id: str, me: User):
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(404, "run not found")
    row = runs_service.get_run(db, rid)
    if row is None or not runs_service.can_view_public_run(viewer=me, run=row):
        raise HTTPException(404, "run not found")
    return row


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    row = _require_owned(db, run_id, me)
    params = row.params or {}
    return {
        "id": str(row.id),
        "ticker": row.ticker,
        "trade_date": params.get("trade_date"),
        "asset_type": params.get("asset_type"),
        "analysts": params.get("analysts"),
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "reports": row.reports or {},
        "final_state": row.result,
        "error": row.error_message,
    }


def _cursor_from(request: Request) -> int:
    """Seed the cursor from Last-Event-ID so a reconnect resumes without gaps."""
    raw = request.headers.get("last-event-id")
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _stream_session_factory():
    """Indirection point so tests can inject their session factory.

    The SSE generator outlives the request-scoped `get_db` session, so it opens
    its own. That bypasses DI — hence this seam. Mirrors slice 1's
    `_session_factory=` override in `_persist_report`.
    """
    return get_session_factory()


def _frame(ev) -> str:
    data = {
        "seq": ev.seq,
        "ts": ev.created_at.isoformat() if ev.created_at else None,
        "type": ev.type,
        **(ev.payload or {}),
    }
    return f"id: {ev.seq}\nevent: {ev.type}\ndata: {json.dumps(data)}\n\n"


@router.get("/runs/{run_id}/stream")
async def stream_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    row = _require_owned(db, run_id, me)
    rid = row.id
    cursor = _cursor_from(request)

    async def event_gen():
        nonlocal cursor
        sf = _stream_session_factory()
        idle = 0.0
        while True:
            # §5.3: read status BEFORE events. A terminal status observed here
            # implies the worker already wrote every event, so the events read
            # below cannot miss any.
            with sf() as s:
                current = runs_service.get_run(s, rid)
                status = current.status if current is not None else "failed"
                batch = events_service.list_events(s, run_id=rid, after_seq=cursor)

            if batch:
                for ev in batch:
                    cursor = ev.seq
                    yield _frame(ev)
                idle = 0.0
                continue  # drain fully before considering termination

            if status in TERMINAL:
                yield f"event: close\ndata: {json.dumps({'status': status})}\n\n"
                return

            await asyncio.sleep(POLL_SECONDS)
            idle += POLL_SECONDS
            if idle >= KEEPALIVE_SECONDS:
                idle = 0.0
                yield ": keep-alive\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
