"""Server-side PDF export of research conversations and debates."""
from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from pallisade_core.research_history import service as research_history
from web.api.deps import get_current_user, get_db
from web.api.services.pdf import (
    AnswerView,
    ClaimView,
    MessageView,
    RecordView,
    ResearchConversationView,
    render_research_pdf,
)

router = APIRouter(tags=["export"])


def _slug(text: str, fallback: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip()).strip("-").lower()
    return s[:60] or fallback


def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )


def _answer_view(answer: dict) -> AnswerView:
    records_by_id = {r["id"]: r for r in answer.get("records", [])}

    def _record_view(rid: str) -> RecordView | None:
        r = records_by_id.get(rid)
        if r is None:
            return None
        prov = r.get("provenance") or {}
        return RecordView(
            capability=str(r.get("capability", "")),
            key=str(r.get("key", "")),
            value=str(r.get("value", "")),
            source=str(prov.get("source", "")),
            locator=str(prov.get("locator", "")),
            as_of=prov.get("as_of"),
            detail=str(prov.get("detail", "")),
        )

    claims = [
        ClaimView(
            text=c.get("text", ""),
            records=[rv for rid in c.get("record_ids", []) if (rv := _record_view(rid))],
        )
        for c in answer.get("claims", [])
    ]
    return AnswerView(
        question=answer.get("question", ""),
        claims=claims,
        sources_used=list(answer.get("sources_used", [])),
        sources_unavailable=list(answer.get("sources_unavailable", [])),
        gaps=[g.get("note", "") if isinstance(g, dict) else str(g) for g in answer.get("gaps", [])],
    )


@router.get("/export/research/{conversation_id}")
def export_research(
    conversation_id: str,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
) -> Response:
    row = research_history.get_conversation(db, user=me, conversation_id=conversation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = [
        MessageView(
            role=m.get("role", ""),
            content=m.get("content", ""),
            answer=_answer_view(m["answer"]) if m.get("answer") else None,
        )
        for m in (row.payload or [])
    ]
    view = ResearchConversationView(
        title=row.title, generated_at=date.today().isoformat(), messages=messages
    )
    return _pdf_response(render_research_pdf(view), _slug(row.title, "research"))
