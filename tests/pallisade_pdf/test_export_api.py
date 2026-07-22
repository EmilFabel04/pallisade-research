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
