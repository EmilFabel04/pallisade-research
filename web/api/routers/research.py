from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from pallisade_connections.resolver import resolve_for_org
from pallisade_core.research_history import service as history_service
from pallisade_core.settings import get_settings
from pallisade_core.users.models import User
from pallisade_research.chat import converse
from pallisade_research.engine import answer
from pallisade_research.models import CitedAnswer
from pallisade_research.planner import plan
from web.api.deps import get_current_user, get_db

router = APIRouter(tags=["research"])

# --- source wiring: per-org connected sources come from resolve_for_org(db, user.org_id)
# (Task 9's connections API + Task 7's resolver); yfinance is always available as a
# built-in fallback. See pallisade_connections/resolver.py. ---
KNOWN_TICKERS = frozenset({"AAPL", "NPN.JO", "SOL.JO", "CPI.JO"})


_LLM: Any = "uninit"


def _llm():
    """Lazily build an Anthropic client; None if unavailable (chat degrades)."""
    global _LLM
    if _LLM == "uninit":
        try:
            import anthropic

            _LLM = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
        except Exception:
            _LLM = None
    return _LLM


def _serialize(result: CitedAnswer) -> dict:
    return {
        "question": result.question,
        "claims": [{"text": c.text, "record_ids": list(c.record_ids)} for c in result.claims],
        "records": [
            {
                "id": r.id,
                "capability": r.capability,
                "key": r.key,
                "value": r.value,
                "provenance": {
                    "source": r.provenance.source,
                    "locator": r.provenance.locator,
                    "as_of": r.provenance.as_of.isoformat() if r.provenance.as_of else None,
                    "detail": r.provenance.detail,
                    "tier": r.provenance.tier,
                    "liveness": r.provenance.liveness,
                },
            }
            for r in result.records
        ],
        "gaps": [{"note": g.note} for g in result.gaps],
        "sources_used": list(result.sources_used),
        "sources_unavailable": list(result.sources_unavailable),
    }


class AskRequest(BaseModel):
    question: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    deep: bool = False


# Login is disabled (see web/api/deps.py): get_current_user resolves to a stable
# default account, so these endpoints work without a real session while still
# scoping sources to that account's org via resolve_for_org.
@router.post("/research/ask")
def ask(req: AskRequest, db: Session = Depends(get_db),
        user: User = Depends(get_current_user)) -> dict:
    resolved = resolve_for_org(db, user.org_id)
    result = answer(plan(req.question, KNOWN_TICKERS), resolved.client_config, resolved.registry)
    data = _serialize(result)
    data["sources_unavailable"] = sorted(set(data["sources_unavailable"]) | set(resolved.sources_unavailable))
    return data


@router.post("/research/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db),
         user: User = Depends(get_current_user)) -> dict:
    settings = get_settings()
    resolved = resolve_for_org(db, user.org_id)
    turn = converse(
        [m.model_dump() for m in req.history],
        req.message,
        config=resolved.client_config,
        registry=resolved.registry,
        known_tickers=KNOWN_TICKERS,
        sdk=_llm(),
        plan_model=settings.query_rewrite_model,
        narrate_model=settings.chat_model,
        depth="deep" if req.deep else "shallow",
        web_enabled=bool(os.environ.get("WEB_SEARCH_API_KEY")),
        web_model=settings.chat_model,
        verify_model=settings.chat_model,
    )
    q = turn["query"]
    ans = _serialize(turn["answer"])
    ans["sources_unavailable"] = sorted(set(ans["sources_unavailable"]) | set(resolved.sources_unavailable))
    return {
        "assistant": turn["assistant"],
        "query": {"ticker": q.ticker, "capabilities": list(q.capabilities), "standalone": q.question},
        "answer": ans,
        "verification": turn["verification"],
    }


# ─── conversation history (per-user, cross-device) ───────────────────────────
class SaveConversationRequest(BaseModel):
    id: uuid.UUID | None = None
    title: str
    messages: list[Any] = []


def _summary(row) -> dict:
    return {"id": str(row.id), "title": row.title, "updated_at": row.updated_at.isoformat()}


@router.post("/research/conversations")
def save_conversation(req: SaveConversationRequest, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)) -> dict:
    row = history_service.upsert_conversation(
        db, user=user, conversation_id=req.id, title=req.title or "Untitled", messages=req.messages,
    )
    db.commit()
    return _summary(row)


@router.get("/research/conversations")
def list_conversations(db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)) -> list[dict]:
    return [_summary(r) for r in history_service.list_conversations(db, user=user)]


@router.get("/research/conversations/{conversation_id}")
def get_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)) -> dict:
    row = history_service.get_conversation(db, user=user, conversation_id=conversation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {**_summary(row), "messages": row.payload}


@router.delete("/research/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)) -> Response:
    if not history_service.delete_conversation(db, user=user, conversation_id=conversation_id):
        raise HTTPException(status_code=404, detail="conversation not found")
    db.commit()
    return Response(status_code=204)
