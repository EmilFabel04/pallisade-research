import uuid

from pallisade_connections.models import default_org_id
from pallisade_connections.resolver import resolve_for_org
from pallisade_core.documents.models import Document


def _mk_doc(org_id, uploader_id, status):
    return Document(
        org_id=org_id, deal_id=None, uploader_id=uploader_id,
        filename="model.xlsx", storage_key="k", content_type="application/vnd.ms-excel",
        byte_size=10, sha256=uuid.uuid4().hex, source_kind="xlsx", status=status,
    )


def test_documents_registered_when_ready_doc_exists(db, make_user):
    org_id = default_org_id(db)
    uploader = make_user()
    db.add(_mk_doc(org_id, uploader.id, "ready"))
    db.commit()

    resolved = resolve_for_org(db, org_id)

    assert "documents" in resolved.registry
    assert resolved.registry["documents"].tier == 1


def test_documents_not_registered_without_ready_doc(db, make_user):
    org_id = default_org_id(db)
    uploader = make_user()
    db.add(_mk_doc(org_id, uploader.id, "parsing"))  # not ready
    db.commit()

    resolved = resolve_for_org(db, org_id)

    assert "documents" not in resolved.registry
