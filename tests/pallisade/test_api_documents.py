import pytest

from pallisade_core.deals.models import Deal
from pallisade_core.documents.models import Document


@pytest.fixture
def deal(db, make_user):
    u = make_user()
    d = Deal(name="X", target_company="Y", deal_type="lbo",
             deal_lead_id=u.id, status="screening")
    db.add(d); db.flush()
    return d, u


@pytest.mark.asyncio
async def test_upload_text_pdf_returns_201_and_creates_pending_doc(client_for, deal, make_user):
    d, lead = deal
    from web.api.routers.documents import router as docs_router
    from web.api.deps import get_current_user
    client = client_for([("/api", docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: lead

    payload = b"%PDF-1.7\nfake but starts right"
    r = await client.post(
        f"/api/deals/{d.id}/documents",
        files={"file": ("CIM.pdf", payload, "application/pdf")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "CIM.pdf"
    assert body["status"] == "pending"
    assert body["source_kind"] in ("pdf_text", "pdf_scan", "pdf_unknown")


@pytest.mark.asyncio
async def test_upload_duplicate_returns_409(client_for, deal, db):
    d, lead = deal
    from web.api.routers.documents import router as docs_router
    from web.api.deps import get_current_user
    client = client_for([("/api", docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: lead

    payload = b"%PDF-1.7\nhello"
    r1 = await client.post(f"/api/deals/{d.id}/documents",
                           files={"file": ("a.pdf", payload, "application/pdf")})
    assert r1.status_code == 201
    r2 = await client.post(f"/api/deals/{d.id}/documents",
                           files={"file": ("b.pdf", payload, "application/pdf")})
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_non_team_member_gets_404(client_for, deal, make_user):
    d, lead = deal
    intruder = make_user()
    from web.api.routers.documents import router as docs_router
    from web.api.deps import get_current_user
    client = client_for([("/api", docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: intruder

    r = await client.get(f"/api/deals/{d.id}/documents")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_unsupported_content_type_returns_415(client_for, deal):
    d, lead = deal
    from web.api.routers.documents import router as docs_router
    from web.api.deps import get_current_user
    client = client_for([("/api", docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: lead

    r = await client.post(f"/api/deals/{d.id}/documents",
                          files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_oversize_upload_returns_413(client_for, deal, monkeypatch):
    d, lead = deal
    from web.api.routers.documents import router as docs_router
    from web.api.deps import get_current_user
    # Shrink the cap for the test.
    monkeypatch.setenv("PALLISADE_MAX_UPLOAD_MB", "0")
    from pallisade_core import settings as smod
    smod.get_settings.cache_clear()

    client = client_for([("/api", docs_router)])
    client._transport.app.dependency_overrides[get_current_user] = lambda: lead

    r = await client.post(f"/api/deals/{d.id}/documents",
                          files={"file": ("a.pdf", b"%PDF-1.7\nx" * 100, "application/pdf")})
    assert r.status_code == 413
