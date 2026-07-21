import pytest
from pallisade_connections.models import default_org_id
from pallisade_core.documents import service as docs_service
from pallisade_core.documents.models import Document, ProcessingJob
from sqlalchemy import select


def test_create_org_document_is_deal_null_and_enqueues_parse(db, make_user):
    user = make_user()
    org_id = default_org_id(db)

    doc = docs_service.create_org_document(
        db, org_id=org_id, uploader=user,
        filename="model.xlsx", content_type="application/octet-stream",
        data=b"hello-org-doc", source_kind="xlsx",
    )
    db.flush()

    assert doc.org_id == org_id
    assert doc.deal_id is None
    assert doc.status == "pending"
    assert doc.storage_key == f"orgs/{org_id}/docs/{doc.id}/model.xlsx"

    job = db.execute(
        select(ProcessingJob).where(ProcessingJob.document_id == doc.id)
    ).scalar_one()
    assert job.job_type == "parse_document"


def test_create_org_document_dedups_on_org_sha(db, make_user):
    user = make_user()
    org_id = default_org_id(db)
    docs_service.create_org_document(
        db, org_id=org_id, uploader=user, filename="a.xlsx",
        content_type="application/octet-stream", data=b"same-bytes", source_kind="xlsx",
    )
    db.flush()
    with pytest.raises(docs_service.DuplicateDocument) as exc:
        docs_service.create_org_document(
            db, org_id=org_id, uploader=user, filename="b.xlsx",
            content_type="application/octet-stream", data=b"same-bytes", source_kind="xlsx",
        )
    assert "org" in str(exc.value)
