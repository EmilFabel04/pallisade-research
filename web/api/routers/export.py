"""Server-side PDF export of research conversations and debates."""
from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from pallisade_core.research_history import service as research_history
from pallisade_core.runs import events as events_service
from pallisade_core.runs import service as runs_service
from web.api.deps import get_current_user, get_db
from web.api.services.pdf import (
    AnswerView,
    ClaimView,
    DebateView,
    MessageView,
    RecordView,
    ReportView,
    ResearchConversationView,
    TurnView,
    render_debate_pdf,
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


_REPORT_LABELS = {
    "market_report": "Market",
    "sentiment_report": "Sentiment",
    "news_report": "News",
    "fundamentals_report": "Fundamentals",
    "investment_plan": "Investment Plan",
    "trader_investment_plan": "Trader Plan",
}


def _parse_verdict(text: str | None) -> dict:
    """Pull labeled fields (e.g. 'Rating: Buy') out of the final decision report."""
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            key = k.strip().lstrip("*# ").strip()
            if key in {"Rating", "Conviction", "Fair Value", "Time Horizon"}:
                out[key] = v.strip()
    return out


@router.get("/export/debate/{run_id}")
def export_debate(
    run_id: str,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
) -> Response:
    run = runs_service.get_run(db, run_id)
    if run is None or not runs_service.can_view_public_run(viewer=me, run=run):
        raise HTTPException(status_code=404, detail="Run not found")

    reports = run.reports or {}
    params = run.params or {}
    report_views = [
        ReportView(key=k, label=_REPORT_LABELS.get(k, k.replace("_", " ").title()), markdown=reports[k])
        for k in _REPORT_LABELS
        if reports.get(k)
    ]
    turns = [
        TurnView(speaker=ev.payload.get("speaker", ""), round=int(ev.payload.get("round", 0)),
                 text=ev.payload.get("text", ""))
        for ev in events_service.list_events(db, run_id=run.id, after_seq=0)
        if ev.type == "turn" and ev.payload.get("phase") == "invest"
    ]
    view = DebateView(
        ticker=run.ticker or "—",
        trade_date=params.get("trade_date") or "",
        generated_at=date.today().isoformat(),
        verdict=_parse_verdict(reports.get("final_trade_decision")),
        reports=report_views,
        turns=turns,
    )
    filename = _slug(f"{run.ticker}-debate-{params.get('trade_date') or ''}", "debate")
    return _pdf_response(render_debate_pdf(view), filename)
