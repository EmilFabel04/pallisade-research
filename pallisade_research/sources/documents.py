from __future__ import annotations

from pallisade_core.rag.retrieve import retrieve_passages
from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import ALL_CAPABILITIES, CAP_RESEARCH

_SNIPPET_LEN = 280


class DocumentsSource:
    """Tier-1 source over the org's uploaded/synced document corpus.

    Retrieval-only: semantic-searches the whole org corpus using the question
    text (ticker folded in). A similarity score floor guards against pulling a
    weakly-related (e.g. wrong-company) passage. The document IS the vendor's
    artifact, so provenance cites the file itself with no vendor tag.
    """

    source = "documents"
    tier = 1
    capabilities = ALL_CAPABILITIES

    def __init__(self, session, org_id, *, retriever=retrieve_passages, k: int = 8, min_score: float = 0.35):
        self._session = session
        self._org_id = org_id
        self._retriever = retriever
        self._k = k
        self._min_score = min_score

    def fetch(self, query: ResearchQuery) -> list[Record]:
        text = f"{query.ticker or ''} {query.question}".strip()
        passages = self._retriever(
            self._session, org_id=self._org_id, query=text, k=self._k,
        )
        out: list[Record] = []
        for p in passages:
            if p.score < self._min_score:
                continue
            page = f" p.{p.page_from}" if p.page_from is not None else ""
            out.append(
                Record(
                    id=f"doc-{p.chunk_id}",
                    capability=CAP_RESEARCH,
                    key=f"document:{p.filename}#{p.chunk_id}",
                    value=p.text[:_SNIPPET_LEN],
                    provenance=Provenance(
                        source="documents",
                        locator=f"{p.filename}{page}",
                        as_of=p.doc_updated_at.date() if p.doc_updated_at else None,
                        detail=p.filename,
                        tier=1,
                        liveness="static",
                    ),
                )
            )
        return out
