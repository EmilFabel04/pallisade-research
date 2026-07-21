from datetime import datetime, timezone

from pallisade_core.rag.retrieve import Passage
from pallisade_research.models import ResearchQuery
from pallisade_research.sources.base import ALL_CAPABILITIES, CAP_RESEARCH
from pallisade_research.sources.documents import DocumentsSource


def _passage(chunk_id, score, filename="Aswan-FactSet-model.xlsx"):
    return Passage(
        chunk_id=chunk_id, document_id="d1", filename=filename,
        page_from=3, page_to=3, sheet_name=None, text="Revenue grew 12%.",
        score=score, doc_updated_at=datetime(2026, 7, 17, tzinfo=timezone.utc),
    )


def test_documents_source_metadata():
    src = DocumentsSource(session=object(), org_id="org-1")
    assert src.source == "documents"
    assert src.tier == 1
    assert src.capabilities == ALL_CAPABILITIES


def test_fetch_drops_below_score_floor():
    calls = {}

    def fake_retriever(session, *, org_id, query, k, embedder=None):
        calls["query"] = query
        return [_passage("c1", 0.80), _passage("c2", 0.10)]

    src = DocumentsSource(session=object(), org_id="org-1", retriever=fake_retriever, min_score=0.35)
    q = ResearchQuery(question="How is revenue?", ticker="AAPL", capabilities=("fundamentals",))
    recs = src.fetch(q)

    assert [r.provenance.locator for r in recs]           # exactly the strong passage kept
    assert len(recs) == 1
    rec = recs[0]
    assert rec.capability == CAP_RESEARCH
    assert rec.key == "document:Aswan-FactSet-model.xlsx#c1"
    assert rec.provenance.tier == 1
    assert rec.provenance.liveness == "static"
    assert rec.provenance.source == "documents"
    assert "AAPL" in calls["query"] and "revenue" in calls["query"].lower()


def test_fetch_empty_when_no_passages():
    src = DocumentsSource(
        session=object(), org_id="org-1",
        retriever=lambda *a, **k: [], min_score=0.35,
    )
    q = ResearchQuery(question="q", ticker="AAPL", capabilities=("fundamentals",))
    assert src.fetch(q) == []
