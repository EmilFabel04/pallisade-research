from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from pallisade_core.memo_checks import service as memo_service
from pallisade_core.memo_checks.models import MemoCheck, MemoClaimResult
from pallisade_core.users.models import User
from web.api.deps import get_current_user, get_db

router = APIRouter(tags=["memo-checks"])


class CreateBody(BaseModel):
    memo_text: str | None = Field(default=None, max_length=200_000)
    memo_document_id: uuid.UUID | None = None
    backing_document_ids: list[uuid.UUID] = Field(default_factory=list)
    scope: str = Field(pattern="^(attached|folder|both)$")

    @model_validator(mode="after")
    def _need_memo_text(self):
        # Memo text is required. Supplying a memo purely as an uploaded document
        # (memo_document_id with no text) is deferred to the UI/Drive slice, which
        # will parse the memo document to text before creating the check. Accepting
        # it here would silently produce an empty report.
        if not (self.memo_text and self.memo_text.strip()):
            raise ValueError("memo_text is required")
        return self

    @model_validator(mode="after")
    def _need_backing_docs_for_attached_scope(self):
        if self.scope in ("attached", "both") and not self.backing_document_ids:
            raise ValueError(
                "backing_document_ids is required when scope is 'attached' or 'both'"
            )
        return self


@router.post("/memo-checks", status_code=201)
def create_check(body: CreateBody, db: Session = Depends(get_db),
                 me: User = Depends(get_current_user)):
    check = memo_service.create_memo_check(
        db, org_id=me.org_id, created_by=me.id,
        memo_text=(body.memo_text or ""), memo_document_id=body.memo_document_id,
        backing_document_ids=body.backing_document_ids, scope=body.scope,
    )
    db.commit()
    db.refresh(check)
    return memo_service.serialize_check(check)


@router.get("/memo-checks/{check_id}")
def get_check(check_id: uuid.UUID, db: Session = Depends(get_db),
              me: User = Depends(get_current_user)):
    check = db.get(MemoCheck, check_id)
    if check is None or check.org_id != me.org_id:
        raise HTTPException(404, "memo check not found")
    results = db.execute(
        select(MemoClaimResult).where(MemoClaimResult.check_id == check.id)
        .order_by(MemoClaimResult.char_start)
    ).scalars().all()
    return {
        "check": memo_service.serialize_check(check),
        "results": [memo_service.serialize_result(r) for r in results],
    }


@router.get("/memo-checks")
def list_checks(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    rows = db.execute(
        select(MemoCheck).where(MemoCheck.org_id == me.org_id)
        .order_by(MemoCheck.created_at.desc()).limit(50)
    ).scalars().all()
    return {"checks": [memo_service.serialize_check(c) for c in rows]}
