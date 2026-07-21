import pytest
from web.api.deps import get_current_user
from web.api.routers.org_documents import router as org_docs_router


def _make_other_org_user(db):
    """Creates a user in a brand-new (different-from-default) org."""
    from pallisade_connections.models import Organization
    from pallisade_core.auth.hashing import hash_password
    from pallisade_core.users.models import User

    other_org = Organization(name="OtherOrg")
    db.add(other_org)
    db.flush()
    intruder = User(
        email="intruder@x.io",
        name="I",
        role="member",
        password_hash=hash_password("x"),
        must_change_password=False,
        org_id=other_org.id,
    )
    db.add(intruder)
    db.flush()
    return intruder


@pytest.mark.asyncio
async def test_org_document_upload_list_delete(client_for, db, make_user):
    u = make_user()
    client = client_for([("/api", org_docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    # upload (bytes tagged as xlsx — classifier keys off mime/extension, no real parse in-request)
    files = {"file": ("model.xlsx", b"org-doc-bytes",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = await client.post("/api/org/documents", files=files)
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["source_kind"] == "xlsx"
    assert doc["status"] == "pending"
    doc_id = doc["id"]

    listed = await client.get("/api/org/documents")
    assert listed.status_code == 200
    assert any(d["id"] == doc_id for d in listed.json()["documents"])

    gone = await client.delete(f"/api/org/documents/{doc_id}")
    assert gone.status_code == 204
    after = await client.get("/api/org/documents")
    assert all(d["id"] != doc_id for d in after.json()["documents"])


@pytest.mark.asyncio
async def test_delete_other_org_document_returns_404(client_for, db, make_user):
    u = make_user()
    intruder = _make_other_org_user(db)
    client = client_for([("/api", org_docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    files = {"file": ("m.xlsx", b"bytes-delete-other-org",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = await client.post("/api/org/documents", files=files)
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    client._transport.app.dependency_overrides[get_current_user] = lambda: intruder
    denied = await client.delete(f"/api/org/documents/{doc_id}")
    assert denied.status_code == 404

    client._transport.app.dependency_overrides[get_current_user] = lambda: u
    listed = await client.get("/api/org/documents")
    assert any(d["id"] == doc_id for d in listed.json()["documents"])


@pytest.mark.asyncio
async def test_list_is_org_scoped(client_for, db, make_user):
    u = make_user()
    intruder = _make_other_org_user(db)
    client = client_for([("/api", org_docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    files = {"file": ("m.xlsx", b"bytes-list-scoped",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = await client.post("/api/org/documents", files=files)
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    client._transport.app.dependency_overrides[get_current_user] = lambda: intruder
    listed = await client.get("/api/org/documents")
    assert listed.status_code == 200
    assert all(d["id"] != doc_id for d in listed.json()["documents"])


@pytest.mark.asyncio
async def test_double_delete_returns_404(client_for, db, make_user):
    u = make_user()
    client = client_for([("/api", org_docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    files = {"file": ("m.xlsx", b"bytes-double-delete",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = await client.post("/api/org/documents", files=files)
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    first = await client.delete(f"/api/org/documents/{doc_id}")
    assert first.status_code == 204

    second = await client.delete(f"/api/org/documents/{doc_id}")
    assert second.status_code == 404
