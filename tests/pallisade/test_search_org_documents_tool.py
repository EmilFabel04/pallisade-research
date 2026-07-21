from contextlib import contextmanager

from pallisade_core.rag.retrieve import Passage
import tradingagents.agents.utils.documents_tool as dt


@contextmanager
def _fake_session():
    yield object()


def _passage(text, filename="model.xlsx", page=3, score=0.9):
    return Passage(
        chunk_id="c1", document_id="d1", filename=filename,
        page_from=page, page_to=page, sheet_name=None, text=text, score=score,
    )


def test_returns_cited_passages(monkeypatch):
    monkeypatch.setattr(dt, "_get_config", lambda: {"org_id": "org-1"})
    monkeypatch.setattr(dt, "_session_scope", _fake_session)
    monkeypatch.setattr(dt, "_retriever", lambda s, **k: [_passage("Revenue grew 12%.")])
    out = dt.search_org_documents.invoke({"query": "revenue"})
    assert "Revenue grew 12%." in out
    assert "model.xlsx" in out and "p.3" in out


def test_no_org_returns_notice(monkeypatch):
    monkeypatch.setattr(dt, "_get_config", lambda: {})
    out = dt.search_org_documents.invoke({"query": "revenue"})
    assert "no org" in out.lower() or "no document" in out.lower()


def test_empty_corpus_returns_notice(monkeypatch):
    monkeypatch.setattr(dt, "_get_config", lambda: {"org_id": "org-1"})
    monkeypatch.setattr(dt, "_session_scope", _fake_session)
    monkeypatch.setattr(dt, "_retriever", lambda s, **k: [])
    out = dt.search_org_documents.invoke({"query": "revenue"})
    assert "no document" in out.lower()
