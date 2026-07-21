"""Tests for pallisade_core.library.service.ingest_run."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from pallisade_core.library.models import LibraryChunk, LibraryDocument
from pallisade_core.library import service as lib_service
from pallisade_core.rag.embeddings import FakeEmbedder
from pallisade_core.runs.models import EvaluationRun

# Seven library kinds; one entry will have an empty body to test filtering.
REPORTS = {
    "market_report": "Equities in South Africa showed resilience this quarter.",
    "sentiment_report": "Retail investor sentiment is broadly positive.",
    "news_report": "",  # empty — should NOT be inserted
    "fundamentals_report": "Revenue grew 12% YoY; margins remain healthy.",
    "investment_plan": "Recommend a long position with a 12-month horizon.",
    "trader_investment_plan": "Enter at open; set stop-loss at 5% below entry.",
    "final_trade_decision": "BUY NPN.JO — high conviction.",
}


@pytest.fixture()
def make_public_run(db, make_user):
    """Create a public EvaluationRun row."""

    def _make(ticker: str = "NPN.JO", *, user=None) -> EvaluationRun:
        owner = user or make_user()
        run = EvaluationRun(
            mode="public",
            user_id=owner.id,
            ticker=ticker,
            status="queued",
        )
        db.add(run)
        db.flush()
        return run

    return _make


def test_ingest_run_creates_six_documents(db, make_public_run, monkeypatch):
    """ingest_run returns 6 (news_report body is empty) and creates 6 rows."""
    fake = FakeEmbedder(dim=1024)
    monkeypatch.setattr(lib_service, "build_default_embedder", lambda: fake)

    run = make_public_run()
    count = lib_service.ingest_run(db, run=run, reports=REPORTS)

    assert count == 6

    docs = db.execute(
        select(LibraryDocument).where(LibraryDocument.run_id == run.id)
    ).scalars().all()
    assert len(docs) == 6

    kinds = {d.kind for d in docs}
    assert "news_report" not in kinds


def test_ingest_run_is_idempotent(db, make_public_run, monkeypatch):
    """Second call to ingest_run returns 0 and total stays at 6."""
    fake = FakeEmbedder(dim=1024)
    monkeypatch.setattr(lib_service, "build_default_embedder", lambda: fake)

    run = make_public_run()
    lib_service.ingest_run(db, run=run, reports=REPORTS)
    second = lib_service.ingest_run(db, run=run, reports=REPORTS)

    assert second == 0

    total = db.execute(
        select(LibraryDocument).where(LibraryDocument.run_id == run.id)
    ).scalars().all()
    assert len(total) == 6


def test_ingest_run_creates_chunks_with_embeddings(db, make_public_run, monkeypatch):
    """At least one LibraryChunk row exists and all have non-None embeddings."""
    fake = FakeEmbedder(dim=1024)
    monkeypatch.setattr(lib_service, "build_default_embedder", lambda: fake)

    run = make_public_run()
    lib_service.ingest_run(db, run=run, reports=REPORTS)

    # Fetch chunks for this run via the docs.
    doc_ids = list(
        db.execute(
            select(LibraryDocument.id).where(LibraryDocument.run_id == run.id)
        ).scalars().all()
    )
    chunks = db.execute(
        select(LibraryChunk).where(LibraryChunk.library_doc_id.in_(doc_ids))
    ).scalars().all()

    assert len(chunks) >= 1
    assert all(c.embedding is not None for c in chunks)
