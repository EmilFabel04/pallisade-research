import uuid
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from web.api.deps import get_current_user, get_db
from web.api.routers import research


def _client(monkeypatch, resolved):
    # ask/chat now resolve sources via resolve_for_org(db, user.org_id) (Task 10);
    # stub that seam plus the db/user deps so the router is exercised in isolation,
    # without a real Postgres session or an authenticated request.
    monkeypatch.setattr(research, "resolve_for_org", lambda db, org_id: resolved)
    monkeypatch.setattr(research, "KNOWN_TICKERS", frozenset({"AAPL"}))

    app = FastAPI()
    app.include_router(research.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(org_id=uuid.uuid4())
    return TestClient(app)


def test_ask_returns_cited_cross_source_answer(monkeypatch):
    # Deterministic per-org registry: yfinance (fundamentals) + holdings, standing in
    # for what resolve_for_org would return for an org with those sources connected.
    from pallisade_connections.resolver import ResolvedSources
    from pallisade_research.sources.holdings import HoldingsSource
    from pallisade_research.sources.registry import ClientConfig
    from pallisade_research.sources.yfinance_source import YFinanceSource

    registry = {
        "yfinance": YFinanceSource(fetcher=lambda t: {"marketCap": 100}),
        "holdings": HoldingsSource([{"ticker": "AAPL", "units": 10, "value": 1000, "as_of": "2026-06-20"}]),
    }
    resolved = ResolvedSources(
        client_config=ClientConfig(client_id="org-1", enabled_sources=frozenset({"yfinance", "holdings"})),
        registry=registry,
    )

    # A conviction question ("worth holding") legitimately pulls holdings, so this
    # exercises the cross-source path without the (removed) auto-inject of holdings
    # onto every ticker query.
    r = _client(monkeypatch, resolved).post("/api/research/ask", json={"question": "is AAPL worth holding?"})
    assert r.status_code == 200
    body = r.json()
    assert body["question"] == "is AAPL worth holding?"
    assert set(body["sources_used"]) == {"yfinance", "holdings"}
    assert all(c["record_ids"] for c in body["claims"])  # every claim cited
    assert any(rec["provenance"]["source"] == "holdings" for rec in body["records"])
    # tier/liveness must survive serialization so structured consumers can see
    # which answering tier produced a record (final-review Minor (a)).
    holdings_rec = next(rec for rec in body["records"] if rec["provenance"]["source"] == "holdings")
    assert holdings_rec["provenance"]["tier"] == 3
    assert holdings_rec["provenance"]["liveness"] == "live"


def test_chat_uses_resolved_registry(monkeypatch):
    # Same per-org resolution seam as /research/ask (Task 10 rewired chat() to also
    # call resolve_for_org). Prove converse() actually receives the resolved
    # registry/config rather than some module-level default, with no real LLM.
    from pallisade_connections.resolver import ResolvedSources
    from pallisade_research.models import CitedAnswer, ResearchQuery
    from pallisade_research.sources.registry import ClientConfig
    from pallisade_research.sources.yfinance_source import YFinanceSource

    registry = {"yfinance": YFinanceSource(fetcher=lambda t: {"marketCap": 100})}
    resolved = ResolvedSources(
        client_config=ClientConfig(client_id="org-1", enabled_sources=frozenset({"yfinance"})),
        registry=registry,
    )

    turn = {
        "assistant": "hi",
        "query": ResearchQuery(question="q", ticker="AAPL", capabilities=()),
        "answer": CitedAnswer(
            question="q",
            claims=(),
            records=(),
            gaps=(),
            sources_used=(),
            sources_unavailable=(),
        ),
    }
    converse_mock = Mock(return_value=turn)

    client = _client(monkeypatch, resolved)
    monkeypatch.setattr(research, "converse", converse_mock)
    monkeypatch.setattr(research, "_llm", lambda: None)

    r = client.post("/api/research/chat", json={"message": "how is AAPL"})
    assert r.status_code == 200

    assert converse_mock.call_args.kwargs["registry"] is registry
    assert converse_mock.call_args.kwargs["config"] is resolved.client_config


def test_ask_surfaces_resolver_sources_unavailable(monkeypatch):
    # resolve_for_org can report connections that failed to construct (e.g.
    # undecryptable creds) via ResolvedSources.sources_unavailable. ask() must
    # merge that into the response, not just the CitedAnswer's own fetch-time
    # sources_unavailable (Fix 2 of the final-review minors).
    from pallisade_connections.resolver import ResolvedSources
    from pallisade_research.sources.registry import ClientConfig
    from pallisade_research.sources.yfinance_source import YFinanceSource

    registry = {"yfinance": YFinanceSource(fetcher=lambda t: {"marketCap": 100})}
    resolved = ResolvedSources(
        client_config=ClientConfig(client_id="org-1", enabled_sources=frozenset({"yfinance"})),
        registry=registry,
        sources_unavailable=["BrokenSK"],
    )

    r = _client(monkeypatch, resolved).post("/api/research/ask", json={"question": "overview of AAPL"})
    assert r.status_code == 200
    assert "BrokenSK" in r.json()["sources_unavailable"]


def test_chat_surfaces_resolver_sources_unavailable(monkeypatch):
    # Same merge as ask(), but through chat()'s nested "answer" payload.
    from pallisade_connections.resolver import ResolvedSources
    from pallisade_research.models import CitedAnswer, ResearchQuery
    from pallisade_research.sources.registry import ClientConfig
    from pallisade_research.sources.yfinance_source import YFinanceSource

    registry = {"yfinance": YFinanceSource(fetcher=lambda t: {"marketCap": 100})}
    resolved = ResolvedSources(
        client_config=ClientConfig(client_id="org-1", enabled_sources=frozenset({"yfinance"})),
        registry=registry,
        sources_unavailable=["BrokenSK"],
    )

    turn = {
        "assistant": "hi",
        "query": ResearchQuery(question="q", ticker="AAPL", capabilities=()),
        "answer": CitedAnswer(
            question="q",
            claims=(),
            records=(),
            gaps=(),
            sources_used=(),
            sources_unavailable=(),
        ),
    }

    client = _client(monkeypatch, resolved)
    monkeypatch.setattr(research, "converse", Mock(return_value=turn))
    monkeypatch.setattr(research, "_llm", lambda: None)

    r = client.post("/api/research/chat", json={"message": "how is AAPL"})
    assert r.status_code == 200
    assert "BrokenSK" in r.json()["answer"]["sources_unavailable"]
