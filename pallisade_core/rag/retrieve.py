from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from pallisade_core.rag.embeddings import Embedder, build_default_embedder, embed_query



@dataclass(frozen=True)
class Passage:
    chunk_id: str
    document_id: str
    filename: str
    page_from: int | None
    page_to: int | None
    sheet_name: str | None
    text: str
    score: float
    doc_updated_at: datetime | None = None


def retrieve_passages(
    session: Session, *, deal_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None, query: str,
    k: int = 8, document_ids: list[uuid.UUID] | None = None,
    embedder: Embedder | None = None,
) -> list[Passage]:
    if (deal_id is None) == (org_id is None):
        raise ValueError("pass exactly one of deal_id / org_id")
    if document_ids is not None and not document_ids:
        return []

    e = embedder or build_default_embedder()
    qvec = embed_query(query, embedder=e)

    if deal_id is not None:
        corpus_clause = "c.deal_id = :corpus_id"
        corpus_id = str(deal_id)
    else:
        corpus_clause = "c.org_id = :corpus_id"
        corpus_id = str(org_id)

    sql = f"""
        SELECT c.id, c.document_id, d.filename,
               c.page_from, c.page_to, c.sheet_name,
               c.text,
               1 - (c.embedding <=> CAST(:qvec AS vector)) AS score,
               d.updated_at
          FROM document_chunks c
          JOIN documents d ON d.id = c.document_id
         WHERE {corpus_clause}
           AND d.deleted_at IS NULL
           AND d.status = 'ready'
           AND c.embedding IS NOT NULL
    """
    params = {"corpus_id": corpus_id, "qvec": str(qvec), "k": k}
    if document_ids:
        sql += " AND c.document_id = ANY(CAST(:doc_ids AS uuid[]))"
        params["doc_ids"] = [str(d) for d in document_ids]
    sql += " ORDER BY c.embedding <=> CAST(:qvec AS vector) LIMIT :k"

    rows = session.execute(text(sql), params).all()
    return [
        Passage(
            chunk_id=str(r[0]), document_id=str(r[1]), filename=r[2],
            page_from=r[3], page_to=r[4], sheet_name=r[5],
            text=r[6], score=float(r[7]), doc_updated_at=r[8],
        )
        for r in rows
    ]


@dataclass(frozen=True)
class LibraryPassage:
    chunk_id: str
    library_doc_id: str
    kind: str
    ticker: str
    title: str
    text: str
    score: float


def retrieve_for_library_doc(
    session: Session, *, library_doc_id: uuid.UUID, query: str, k: int = 6,
    embedder: Embedder | None = None,
) -> list[LibraryPassage]:
    e = embedder or build_default_embedder()
    qvec = embed_query(query, embedder=e)
    sql = """
        SELECT c.id, c.library_doc_id, d.kind, d.ticker, d.title, c.text,
               1 - (c.embedding <=> CAST(:qvec AS vector)) AS score
          FROM library_chunks c
          JOIN library_documents d ON d.id = c.library_doc_id
         WHERE c.library_doc_id = :doc_id
           AND c.embedding IS NOT NULL
         ORDER BY c.embedding <=> CAST(:qvec AS vector)
         LIMIT :k
    """
    rows = session.execute(text(sql), {
        "doc_id": str(library_doc_id), "qvec": str(qvec), "k": k,
    }).all()
    return [LibraryPassage(
        chunk_id=str(r[0]), library_doc_id=str(r[1]),
        kind=r[2], ticker=r[3], title=r[4], text=r[5], score=float(r[6]),
    ) for r in rows]


def retrieve_for_global(
    session: Session, *, query: str, k: int = 8,
    mentioned_doc_ids: list[uuid.UUID] | None = None,
    embedder: Embedder | None = None,
) -> list[LibraryPassage]:
    e = embedder or build_default_embedder()
    qvec = embed_query(query, embedder=e)
    sql = """
        SELECT c.id, c.library_doc_id, d.kind, d.ticker, d.title, c.text,
               1 - (c.embedding <=> CAST(:qvec AS vector)) AS score
          FROM library_chunks c
          JOIN library_documents d ON d.id = c.library_doc_id
         WHERE c.embedding IS NOT NULL
    """
    params: dict = {"qvec": str(qvec), "k": k}
    if mentioned_doc_ids:
        sql += " AND c.library_doc_id = ANY(CAST(:doc_ids AS uuid[]))"
        params["doc_ids"] = [str(d) for d in mentioned_doc_ids]
    sql += " ORDER BY c.embedding <=> CAST(:qvec AS vector) LIMIT :k"
    rows = session.execute(text(sql), params).all()
    return [LibraryPassage(
        chunk_id=str(r[0]), library_doc_id=str(r[1]),
        kind=r[2], ticker=r[3], title=r[4], text=r[5], score=float(r[6]),
    ) for r in rows]
