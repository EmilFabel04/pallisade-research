"""Library router — list, get-by-id, tickers-with-counts."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from pallisade_core.library.models import LibraryDocument
from pallisade_core.runs.models import EvaluationRun
from pallisade_core.users.models import User
from web.api.deps import get_current_user, get_db

router = APIRouter(prefix="/library", tags=["library"])


def _serialize(doc: LibraryDocument) -> dict:
    return {
        "id": str(doc.id),
        "run_id": str(doc.run_id),
        "ticker": doc.ticker,
        "kind": doc.kind,
        "title": doc.title,
        "created_at": doc.created_at.isoformat(),
        "preview": doc.body_md[:280],
    }


@router.get("/documents")
def list_documents(
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
    ticker: Optional[str] = None,
    kind: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = None,
):
    stmt = select(LibraryDocument)
    if ticker:
        stmt = stmt.where(LibraryDocument.ticker == ticker)
    if kind:
        stmt = stmt.where(LibraryDocument.kind == kind)
    if q:
        safe = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{safe}%"
        stmt = stmt.where(
            LibraryDocument.title.ilike(like, escape="\\")
            | LibraryDocument.ticker.ilike(like, escape="\\")
        )
    if cursor:
        try:
            cur_iso, cur_id = cursor.split("|", 1)
            cur_dt = datetime.fromisoformat(cur_iso)
            stmt = stmt.where(
                (LibraryDocument.created_at < cur_dt)
                | (
                    (LibraryDocument.created_at == cur_dt)
                    & (LibraryDocument.id < uuid.UUID(cur_id))
                )
            )
        except Exception:
            raise HTTPException(400, "bad cursor")
    stmt = (
        stmt.order_by(desc(LibraryDocument.created_at), desc(LibraryDocument.id))
        .limit(limit + 1)
    )
    rows = list(db.execute(stmt).scalars())
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"
        rows = rows[:limit]
    return {"items": [_serialize(d) for d in rows], "next_cursor": next_cursor}


@router.get("/documents/{doc_id}")
def get_document(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    doc = db.get(LibraryDocument, doc_id)
    if doc is None:
        raise HTTPException(404, "library document not found")
    run = db.get(EvaluationRun, doc.run_id)
    out = _serialize(doc)
    out["body_md"] = doc.body_md
    out["source_run"] = (
        {
            "id": str(run.id),
            "ticker": run.ticker,
            "created_at": run.created_at.isoformat(),
        }
        if run
        else None
    )
    return out


@router.get("/tickers")
def list_tickers(
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    stmt = (
        select(LibraryDocument.ticker, func.count().label("n"))
        .group_by(LibraryDocument.ticker)
        .order_by(LibraryDocument.ticker)
    )
    rows = db.execute(stmt).all()
    return {"tickers": [{"ticker": t, "count": int(n)} for t, n in rows]}
