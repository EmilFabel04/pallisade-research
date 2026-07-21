import uuid

import pytest
from pallisade_core.documents.models import ProcessingJob
from web.api.deps import get_current_user
from web.api.routers.memo_checks import router as memo_checks_router
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_and_get_memo_check(client_for, db, make_user):
    u = make_user()
    client = client_for([("/api", memo_checks_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u

    resp = await client.post("/api/memo-checks", json={
        "memo_text": "Revenue is R42.1bn.",
        "backing_document_ids": [],
        "scope": "folder",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "queued"
    check_id = body["id"]

    # A check_memo job was enqueued with the check id in its payload.
    job = db.execute(
        select(ProcessingJob).where(ProcessingJob.job_type == "check_memo")
    ).scalar_one()
    assert job.payload["memo_check_id"] == check_id

    got = await client.get(f"/api/memo-checks/{check_id}")
    assert got.status_code == 200
    assert got.json()["check"]["memo_text"] == "Revenue is R42.1bn."
    assert got.json()["results"] == []


@pytest.mark.asyncio
async def test_create_requires_memo_text(client_for, make_user):
    u = make_user()
    client = client_for([("/api", memo_checks_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u
    resp = await client.post("/api/memo-checks",
                             json={"backing_document_ids": [], "scope": "folder"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_document_only_memo(client_for, make_user):
    # A memo supplied purely as an uploaded document (memo_document_id with no
    # memo_text) is deferred to the UI/Drive slice; the API must reject it now
    # rather than silently running an empty report.
    u = make_user()
    client = client_for([("/api", memo_checks_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u
    resp = await client.post("/api/memo-checks", json={
        "memo_document_id": str(uuid.uuid4()),
        "backing_document_ids": [],
        "scope": "folder",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_attached_scope_without_backing_docs(client_for, make_user):
    u = make_user()
    client = client_for([("/api", memo_checks_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: u
    resp = await client.post("/api/memo-checks", json={
        "memo_text": "Revenue is R42.1bn.",
        "backing_document_ids": [],
        "scope": "attached",
    })
    assert resp.status_code == 422
