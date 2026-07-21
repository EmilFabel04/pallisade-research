from pallisade_connections.models import default_org_id
from pallisade_core.memo_checks.models import MemoCheck, MemoClaimResult
from sqlalchemy import select


def test_memo_check_and_results_persist_and_cascade(db, make_user):
    user = make_user()
    org_id = default_org_id(db)
    check = MemoCheck(
        org_id=org_id, memo_document_id=None, memo_text="Revenue is R42.1bn.",
        backing_document_ids=[], scope="folder", status="queued",
        created_by=user.id,
    )
    db.add(check)
    db.flush()

    db.add(MemoClaimResult(
        check_id=check.id, claim_text="Revenue is R42.1bn",
        claim_value="R42.1bn", verdict="match", source_document_id=None,
        locator="Sheet Model", source_value="R42.1bn", source_as_of=None,
        tier="doc", rationale="agrees", char_start=0, char_end=18,
    ))
    db.flush()

    db.delete(check)
    db.flush()
    remaining = db.execute(select(MemoClaimResult)).scalars().all()
    assert remaining == []
