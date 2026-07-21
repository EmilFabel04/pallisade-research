from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy.orm import Session

from pallisade_core.documents.models import Document, ProcessingJob
from pallisade_core.memo_checks.adjudicate import SourceCandidate, adjudicate
from pallisade_core.memo_checks.extract import extract_figures
from pallisade_core.memo_checks.models import MemoCheck, MemoClaimResult
from pallisade_core.rag.embeddings import Embedder
from pallisade_core.rag.retrieve import Passage, retrieve_passages

log = logging.getLogger(__name__)


def locator_for(p: Passage) -> str:
    if p.sheet_name:
        return f"Sheet {p.sheet_name}"
    if p.page_from is not None:
        span = f"p.{p.page_from}" if p.page_from == p.page_to else f"pp.{p.page_from}-{p.page_to}"
        return span
    return "document"


def handle_check_memo(
    session: Session, job: ProcessingJob, doc: Document | None, *,
    sdk=None, embedder: Embedder | None = None,
) -> None:
    from pallisade_core.settings import get_settings
    settings = get_settings()
    if sdk is None:
        from pallisade_core.memo_checks.sdk import build_memo_sdk
        sdk = build_memo_sdk()

    check_id = uuid.UUID(job.payload["memo_check_id"])
    check = session.get(MemoCheck, check_id)
    if check is None:
        raise RuntimeError(f"memo_check {check_id} not found")

    check.status = "running"
    session.query(MemoClaimResult).filter(MemoClaimResult.check_id == check.id).delete()
    session.flush()

    memo_date: date = check.created_at.date()
    # attached → only the backing docs; folder/both → whole org corpus
    # (the corpus is a superset of any attached docs, so 'both' includes them).
    doc_ids = list(check.backing_document_ids) if check.scope == "attached" else None

    figures = extract_figures(check.memo_text, sdk=sdk, model=settings.memo_check_model)

    for fig in figures:
        passages = retrieve_passages(
            session, org_id=check.org_id, query=fig.claim_text, k=6,
            document_ids=doc_ids, embedder=embedder,
        )
        as_of_by_doc: dict[str, date | None] = {}
        candidates: list[SourceCandidate] = []
        for p in passages:
            if p.document_id not in as_of_by_doc:
                d = session.get(Document, uuid.UUID(p.document_id))
                as_of_by_doc[p.document_id] = d.updated_at.date() if d else None
            candidates.append(SourceCandidate(
                document_id=p.document_id, text=p.text, filename=p.filename,
                locator=locator_for(p), as_of=as_of_by_doc[p.document_id],
            ))

        v = adjudicate(fig, candidates, sdk=sdk, model=settings.memo_check_model,
                       memo_date=memo_date, stale_days=settings.memo_stale_days)
        session.add(MemoClaimResult(
            check_id=check.id, claim_text=fig.claim_text, claim_value=fig.value,
            verdict=v.verdict,
            source_document_id=uuid.UUID(v.source_document_id) if v.source_document_id else None,
            locator=v.locator, source_value=v.source_value,
            source_as_of=v.source_as_of, tier="doc", rationale=v.rationale,
            char_start=fig.char_start, char_end=fig.char_end,
        ))

    check.status = "done"
    session.flush()
