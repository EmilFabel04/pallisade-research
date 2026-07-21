import uuid

from pallisade_connections.models import default_org_id
from pallisade_core.documents import service as docs_service
from pallisade_core.documents.models import DocumentChunk, ProcessingJob
from pallisade_core.memo_checks.models import MemoCheck, MemoClaimResult
from pallisade_core.rag.embeddings import FakeEmbedder
from pallisade_worker.handlers.memo_check import handle_check_memo
from sqlalchemy import select


class _Block:
    def __init__(self, inp):
        self.type = "tool_use"
        self.input = inp


class _Msg:
    def __init__(self, inp):
        self.content = [_Block(inp)]


class FakeSdk:
    """Returns queued tool payloads in call order."""
    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.messages = self

    def create(self, **kwargs):
        return _Msg(self._payloads.pop(0))


def _seed_org_source(db, user, org_id, text="Revenue: R42.1bn"):
    doc = docs_service.create_org_document(
        db, org_id=org_id, uploader=user, filename="model.xlsx",
        content_type="application/octet-stream", data=text.encode(), source_kind="xlsx",
    )
    db.flush()
    doc.status = "ready"
    vec = FakeEmbedder(dim=1024).embed([text], input_type="document")[0]
    db.add(DocumentChunk(document_id=doc.id, org_id=org_id, deal_id=None,
                         chunk_index=0, text=text, token_count=1,
                         sheet_name="Model", embedding=vec))
    db.flush()
    return doc


def test_handler_writes_match_result(db, make_user):
    user = make_user()
    org_id = default_org_id(db)
    src = _seed_org_source(db, user, org_id)

    check = MemoCheck(org_id=org_id, memo_document_id=None,
                      memo_text="Revenue is R42.1bn.", backing_document_ids=[src.id],
                      scope="attached", status="queued", created_by=user.id)
    db.add(check)
    db.flush()
    job = ProcessingJob(job_type="check_memo", document_id=None, status="running",
                        payload={"memo_check_id": str(check.id)})
    db.add(job)
    db.flush()

    sdk = FakeSdk([
        {"figures": [{"claim_text": "Revenue is R42.1bn", "value": "42.1",
                      "unit": "R bn", "char_start": 0, "char_end": 18}]},
        {"found": True, "agrees": True, "candidate_index": 0,
         "source_value": "R42.1bn", "rationale": "agrees"},
    ])
    handle_check_memo(db, job, None, sdk=sdk, embedder=FakeEmbedder(dim=1024))

    db.refresh(check)
    assert check.status == "done"
    results = db.execute(
        select(MemoClaimResult).where(MemoClaimResult.check_id == check.id)
    ).scalars().all()
    assert len(results) == 1
    assert results[0].verdict == "match"
    assert results[0].source_document_id == src.id
    assert results[0].tier == "doc"


def test_scope_both_retrieves_from_corpus_not_just_backing_docs(db, make_user):
    """scope='both' must search the whole org corpus, not only backing_document_ids."""
    user = make_user()
    org_id = default_org_id(db)
    src = _seed_org_source(db, user, org_id)

    check = MemoCheck(org_id=org_id, memo_document_id=None,
                      memo_text="Revenue is R42.1bn.",
                      backing_document_ids=[uuid.uuid4()],  # unrelated doc, NOT the seeded source
                      scope="both", status="queued", created_by=user.id)
    db.add(check)
    db.flush()
    job = ProcessingJob(job_type="check_memo", document_id=None, status="running",
                        payload={"memo_check_id": str(check.id)})
    db.add(job)
    db.flush()

    sdk = FakeSdk([
        {"figures": [{"claim_text": "Revenue is R42.1bn", "value": "42.1",
                      "unit": "R bn", "char_start": 0, "char_end": 18}]},
        {"found": True, "agrees": True, "candidate_index": 0,
         "source_value": "R42.1bn", "rationale": "agrees"},
    ])
    handle_check_memo(db, job, None, sdk=sdk, embedder=FakeEmbedder(dim=1024))

    db.refresh(check)
    assert check.status == "done"
    results = db.execute(
        select(MemoClaimResult).where(MemoClaimResult.check_id == check.id)
    ).scalars().all()
    assert len(results) == 1
    assert results[0].verdict == "match"
    assert results[0].source_document_id == src.id


def test_handler_is_idempotent_on_retry(db, make_user):
    """Retrying a check must not create duplicate MemoClaimResult rows."""
    user = make_user()
    org_id = default_org_id(db)
    src = _seed_org_source(db, user, org_id)

    check = MemoCheck(org_id=org_id, memo_document_id=None,
                      memo_text="Revenue is R42.1bn.", backing_document_ids=[src.id],
                      scope="attached", status="queued", created_by=user.id)
    db.add(check)
    db.flush()
    job = ProcessingJob(job_type="check_memo", document_id=None, status="running",
                        payload={"memo_check_id": str(check.id)})
    db.add(job)
    db.flush()

    def _payloads():
        return FakeSdk([
            {"figures": [{"claim_text": "Revenue is R42.1bn", "value": "42.1",
                          "unit": "R bn", "char_start": 0, "char_end": 18}]},
            {"found": True, "agrees": True, "candidate_index": 0,
             "source_value": "R42.1bn", "rationale": "agrees"},
        ])

    handle_check_memo(db, job, None, sdk=_payloads(), embedder=FakeEmbedder(dim=1024))
    handle_check_memo(db, job, None, sdk=_payloads(), embedder=FakeEmbedder(dim=1024))

    db.refresh(check)
    assert check.status == "done"
    results = db.execute(
        select(MemoClaimResult).where(MemoClaimResult.check_id == check.id)
    ).scalars().all()
    assert len(results) == 1
