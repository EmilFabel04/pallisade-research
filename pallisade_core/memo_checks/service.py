from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from pallisade_core.documents.models import ProcessingJob
from pallisade_core.memo_checks.models import MemoCheck, MemoClaimResult


def create_memo_check(
    session: Session, *, org_id: uuid.UUID, created_by: uuid.UUID,
    memo_text: str, memo_document_id: uuid.UUID | None,
    backing_document_ids: list[uuid.UUID], scope: str,
) -> MemoCheck:
    check = MemoCheck(
        org_id=org_id, created_by=created_by, memo_text=memo_text,
        memo_document_id=memo_document_id, backing_document_ids=backing_document_ids,
        scope=scope, status="queued",
    )
    session.add(check)
    session.flush()
    session.add(ProcessingJob(
        job_type="check_memo", document_id=memo_document_id, status="queued",
        payload={"memo_check_id": str(check.id)},
    ))
    return check


def serialize_check(c: MemoCheck) -> dict:
    return {
        "id": str(c.id), "org_id": str(c.org_id),
        "memo_document_id": str(c.memo_document_id) if c.memo_document_id else None,
        "memo_text": c.memo_text,
        "backing_document_ids": [str(x) for x in c.backing_document_ids],
        "scope": c.scope, "status": c.status,
        "created_at": c.created_at.isoformat(),
    }


def serialize_result(r: MemoClaimResult) -> dict:
    return {
        "claim_text": r.claim_text, "claim_value": r.claim_value, "verdict": r.verdict,
        "source_document_id": str(r.source_document_id) if r.source_document_id else None,
        "locator": r.locator, "source_value": r.source_value,
        "source_as_of": r.source_as_of.isoformat() if r.source_as_of else None,
        "tier": r.tier, "rationale": r.rationale,
        "char_start": r.char_start, "char_end": r.char_end,
    }
