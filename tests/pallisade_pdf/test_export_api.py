from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from web.api.deps import get_current_user, get_db
from web.api.routers import export


def _client(monkeypatch, conversation):
    monkeypatch.setattr(
        export.research_history, "get_conversation",
        lambda db, *, user, conversation_id: conversation,
    )
    app = FastAPI()
    app.include_router(export.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="u1", role="member")
    return TestClient(app)


_CONV = SimpleNamespace(
    title="AAPL overview",
    payload=[
        {"role": "user", "content": "is AAPL worth holding?"},
        {"role": "assistant", "content": "**Yes**.", "answer": {
            "question": "is AAPL worth holding?",
            "claims": [{"text": "Cap is 100.", "record_ids": ["r1"]}],
            "records": [{"id": "r1", "capability": "fundamentals", "key": "cap", "value": "100",
                         "provenance": {"source": "yfinance", "locator": "AAPL/cap", "as_of": "2026-06-20", "detail": ""}}],
            "sources_used": ["yfinance"], "sources_unavailable": [], "gaps": [],
        }},
    ],
)


def test_export_research_returns_pdf(monkeypatch):
    r = _client(monkeypatch, _CONV).get("/api/export/research/abc")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content[:4] == b"%PDF"


def test_export_research_404_when_missing(monkeypatch):
    r = _client(monkeypatch, None).get("/api/export/research/missing")
    assert r.status_code == 404


def _debate_client(monkeypatch, run, events, viewer_role="member"):
    monkeypatch.setattr(export.runs_service, "get_run", lambda db, rid: run)
    monkeypatch.setattr(
        export.runs_service, "can_view_public_run",
        lambda *, viewer, run: run is not None and (viewer.role == "admin" or getattr(run, "user_id", None) == viewer.id),
    )
    monkeypatch.setattr(export.events_service, "list_events", lambda db, *, run_id, after_seq=0: events)
    app = FastAPI()
    app.include_router(export.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="u1", role=viewer_role)
    return TestClient(app)


_RUN = SimpleNamespace(
    id="run1", user_id="u1", ticker="AAPL",
    params={"trade_date": "2026-06-20"},
    reports={"market_report": "**Uptrend**.",
             "final_trade_decision": "Rating: Buy\nConviction: High\nFair Value: $260\nTime Horizon: 12m"},
)
_EVENTS = [
    SimpleNamespace(seq=1, type="turn", payload={"phase": "invest", "speaker": "bull", "round": 1, "text": "Margins up."}),
    SimpleNamespace(seq=2, type="turn", payload={"phase": "invest", "speaker": "bear", "round": 1, "text": "Too pricey."}),
    SimpleNamespace(seq=3, type="report", payload={"key": "market_report", "content": "x"}),
    SimpleNamespace(seq=4, type="turn", payload={"phase": "risk", "speaker": "neutral", "round": 1, "text": "ignore me"}),
]


def test_export_debate_returns_pdf(monkeypatch):
    r = _debate_client(monkeypatch, _RUN, _EVENTS).get("/api/export/debate/run1")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_export_debate_404_when_missing(monkeypatch):
    r = _debate_client(monkeypatch, None, []).get("/api/export/debate/missing")
    assert r.status_code == 404


def test_export_debate_404_when_not_owner(monkeypatch):
    other = SimpleNamespace(id="someone-else", user_id="someone-else", ticker="AAPL", params={}, reports={})
    r = _debate_client(monkeypatch, other, [], viewer_role="member").get("/api/export/debate/run1")
    assert r.status_code == 404
