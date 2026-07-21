from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from pallisade_core.deals import service as deals_service
from pallisade_core.rag.retrieve import retrieve_passages
from pallisade_core.users.models import User
from web.api.deps import get_current_user, get_db

router = APIRouter(tags=["retrieve"])


class RetrieveBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=8, ge=1, le=50)
    document_ids: list[uuid.UUID] | None = None


@router.post("/deals/{deal_id}/retrieve")
def retrieve_endpoint(
    deal_id: uuid.UUID, body: RetrieveBody,
    db: Session = Depends(get_db), me: User = Depends(get_current_user),
):
    deal = deals_service.get_deal(db, deal_id)
    if deal is None or not deals_service.can_view(db, viewer=me, deal=deal):
        raise HTTPException(404, "deal not found")
    passages = retrieve_passages(
        db, deal_id=deal.id, query=body.query, k=body.k,
        document_ids=body.document_ids,
    )
    return {"passages": [
        {
            "chunk_id": p.chunk_id, "document_id": p.document_id,
            "filename": p.filename, "page_from": p.page_from, "page_to": p.page_to,
            "sheet_name": p.sheet_name, "text": p.text, "score": p.score,
        }
        for p in passages
    ]}
