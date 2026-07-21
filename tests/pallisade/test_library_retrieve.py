"""Tests for retrieve_for_library_doc and retrieve_for_global."""
from __future__ import annotations

import pytest

from pallisade_core.library import service as lib_service
from pallisade_core.rag import retrieve as retrieve_mod
from pallisade_core.rag.embeddings import FakeEmbedder
from pallisade_core.runs.models import EvaluationRun

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

SAMPLE_REPORTS_A = {
    "market_report": "Equities in South Africa showed resilience this quarter with strong demand.",
    "fundamentals_report": "Revenue grew 12% YoY; margins remain healthy across all segments.",
}

SAMPLE_REPORTS_B = {
    "investment_plan": "Recommend a long position with a 12-month horizon and careful stop-loss.",
    "final_trade_decision": "BUY NPN.JO — high conviction based on strong fundamentals.",
}


@pytest.fixture()
def fake_embedder():
    return FakeEmbedder(dim=1024)


@pytest.fixture()
def ingested_library_factory(db, make_user, monkeypatch, fake_embedder):
    """Returns a callable that ingests reports into the library and returns the
    first LibraryDocument created for that run."""
    monkeypatch.setattr(lib_service, "build_default_embedder", lambda: fake_embedder)
    monkeypatch.setattr(retrieve_mod, "build_default_embedder", lambda: fake_embedder)

    def _make(reports: dict[str, str], ticker: str = "NPN.JO"):
        owner = make_user()
        run = EvaluationRun(
            mode="public",
            user_id=owner.id,
            ticker=ticker,
            status="done",
        )
        db.add(run)
        db.flush()
        lib_service.ingest_run(db, run=run, reports=reports)
        db.flush()
        # Return all library docs created for this run (sorted by kind for stability).
        from sqlalchemy import select
        from pallisade_core.library.models import LibraryDocument
        docs = db.execute(
            select(LibraryDocument).where(LibraryDocument.run_id == run.id)
        ).scalars().all()
        return docs

    return _make


# ---------------------------------------------------------------------------
# Test 1 — per-doc retrieval scoped to one document
# ---------------------------------------------------------------------------

def test_retrieve_for_library_doc_scoped_to_doc(db, ingested_library_factory, fake_embedder):
    """All returned passages should belong to the queried library_doc_id."""
    docs = ingested_library_factory(SAMPLE_REPORTS_A)
    assert docs, "expected at least one doc to be ingested"

    doc_a = docs[0]
    from pallisade_core.rag.retrieve import retrieve_for_library_doc

    passages = retrieve_for_library_doc(
        db,
        library_doc_id=doc_a.id,
        query="South Africa equities revenue",
        k=6,
        embedder=fake_embedder,
    )

    assert len(passages) >= 1
    for p in passages:
        assert p.library_doc_id == str(doc_a.id), (
            f"Expected all passages to have library_doc_id={doc_a.id!r}, "
            f"got {p.library_doc_id!r}"
        )


# ---------------------------------------------------------------------------
# Test 2 — global retrieval filtered to mentioned_doc_ids
# ---------------------------------------------------------------------------

def test_retrieve_for_global_with_mentioned_doc_ids(db, ingested_library_factory, fake_embedder):
    """When mentioned_doc_ids=[doc_a.id], only doc_a hits are returned."""
    docs_a = ingested_library_factory(SAMPLE_REPORTS_A, ticker="NPN.JO")
    docs_b = ingested_library_factory(SAMPLE_REPORTS_B, ticker="SHP.JO")

    assert docs_a and docs_b

    doc_a = docs_a[0]
    doc_b_ids = {str(d.id) for d in docs_b}

    from pallisade_core.rag.retrieve import retrieve_for_global

    passages = retrieve_for_global(
        db,
        query="revenue growth South Africa equities",
        k=8,
        mentioned_doc_ids=[doc_a.id],
        embedder=fake_embedder,
    )

    assert len(passages) >= 1
    for p in passages:
        assert p.library_doc_id == str(doc_a.id), (
            f"Expected only doc_a passages, got {p.library_doc_id!r}"
        )
        assert p.library_doc_id not in doc_b_ids


# ---------------------------------------------------------------------------
# Test 3 — global retrieval without filter returns hits from both docs
# ---------------------------------------------------------------------------

def test_retrieve_for_global_no_filter_returns_multiple_docs(db, ingested_library_factory, fake_embedder):
    """Without mentioned_doc_ids, retrieval can return chunks from multiple docs."""
    docs_a = ingested_library_factory(SAMPLE_REPORTS_A, ticker="NPN.JO")
    docs_b = ingested_library_factory(SAMPLE_REPORTS_B, ticker="SHP.JO")

    assert docs_a and docs_b

    all_doc_ids_a = {str(d.id) for d in docs_a}
    all_doc_ids_b = {str(d.id) for d in docs_b}

    from pallisade_core.rag.retrieve import retrieve_for_global

    passages = retrieve_for_global(
        db,
        query="investment equities South Africa",
        k=10,
        mentioned_doc_ids=None,
        embedder=fake_embedder,
    )

    assert len(passages) >= 1
    returned_ids = {p.library_doc_id for p in passages}
    # Both doc sets should contribute hits (with k=10 and only a few chunks total).
    from_a = returned_ids & all_doc_ids_a
    from_b = returned_ids & all_doc_ids_b
    assert from_a or from_b, "expected at least one passage from ingested docs"
    # With two runs ingested, we should be drawing from at least two docs total.
    assert len(returned_ids) >= 2, (
        f"Expected passages from at least 2 docs, got: {returned_ids}"
    )
