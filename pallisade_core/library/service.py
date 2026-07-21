from __future__ import annotations

import logging
import re
from typing import Mapping

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from pallisade_core.library.models import LIBRARY_KINDS, LibraryChunk, LibraryDocument
from pallisade_core.rag.chunking import chunk_pages
from pallisade_core.rag.embeddings import build_default_embedder, embed_documents
from pallisade_core.runs.models import EvaluationRun

log = logging.getLogger(__name__)

_MENTION_RE = re.compile(r'@"([^"]+)"|@([\w.\-]+)')


def parse_mentions(text: str) -> list[str]:
    """Return a list of mention strings from *text*.

    Supports two forms:
      * ``@"quoted string"`` — returns ``quoted string``
      * ``@bare_word``       — returns ``bare_word``
    """
    return [a or b for a, b in _MENTION_RE.findall(text)]


def _escape_like(s: str) -> str:
    """Escape LIKE/ILIKE metacharacters so they are treated as literals."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def resolve_mentions(db: Session, titles: list[str]) -> list[LibraryDocument]:
    """Resolve a list of mention strings to :class:`LibraryDocument` rows.

    For each title substring, returns the most-recently-created document whose
    ``title`` contains that substring (case-insensitive).  At most one document
    per unique mention string is returned.
    """
    if not titles:
        return []
    clauses = [
        LibraryDocument.title.ilike(f"%{_escape_like(t)}%", escape="\\")
        for t in titles
    ]
    stmt = (
        select(LibraryDocument)
        .where(or_(*clauses))
        .order_by(LibraryDocument.created_at.desc())
    )
    seen: set[str] = set()
    out: list[LibraryDocument] = []
    for doc in db.execute(stmt).scalars():
        key = next((t for t in titles if t.lower() in doc.title.lower()), None)
        if key is None or key in seen:
            continue
        seen.add(key)
        out.append(doc)
    return out


_TITLE_LABEL: dict[str, str] = {
    "market_report": "Market Report",
    "sentiment_report": "Sentiment Report",
    "news_report": "News Report",
    "fundamentals_report": "Fundamentals Report",
    "investment_plan": "Investment Plan",
    "trader_investment_plan": "Trader Investment Plan",
    "final_trade_decision": "Final Trade Decision",
}


def _title_for(run: EvaluationRun, kind: str) -> str:
    when = run.created_at.strftime("%Y-%m-%d") if run.created_at else ""
    return f"{run.ticker} — {_TITLE_LABEL[kind]} — {when}".strip(" —")


def ingest_run(
    db: Session,
    *,
    run: EvaluationRun,
    reports: Mapping[str, str],
) -> int:
    """Ingest report bodies from a completed public run into the library.

    Returns the number of new ``LibraryDocument`` rows created.  Skips any
    kind that already has a document for this run (idempotent).  Non-public
    runs are silently skipped and return 0.
    """
    if run.mode != "public":
        log.info("skip ingest_run for non-public run %s", run.id)
        return 0

    existing_kinds = set(
        db.execute(
            select(LibraryDocument.kind).where(LibraryDocument.run_id == run.id)
        ).scalars().all()
    )

    embedder = build_default_embedder()
    inserted = 0

    for kind in LIBRARY_KINDS:
        body = (reports.get(kind) or "").strip()
        if not body or kind in existing_kinds:
            continue

        doc = LibraryDocument(
            run_id=run.id,
            ticker=run.ticker,
            kind=kind,
            title=_title_for(run, kind),
            body_md=body,
        )
        db.add(doc)
        db.flush()

        chunks = chunk_pages([(1, body)], target_tokens=500, overlap_tokens=80)
        if chunks:
            embeddings = embed_documents([c.text for c in chunks], embedder=embedder)
            for c, emb in zip(chunks, embeddings):
                db.add(LibraryChunk(
                    library_doc_id=doc.id,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    embedding=emb,
                ))

        inserted += 1

    return inserted
