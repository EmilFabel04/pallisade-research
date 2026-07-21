from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from pallisade_core.db.session import db_session
from web.api.deps import get_db
from web.api.routers.auth import router as auth_router


@pytest.fixture()
def app(db):
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")
    def _override_db():
        yield db
    app.dependency_overrides[get_db] = _override_db
    return app


@pytest.fixture()
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_login_success_sets_cookie(client, make_user, db):
    make_user(email="a@example.com", password="Pass!1234567"); db.flush()
    r = await client.post("/api/auth/login", json={"email": "a@example.com", "password": "Pass!1234567"})
    assert r.status_code == 200
    assert "pallisade_session" in r.cookies
    body = r.json()
    assert body["email"] == "a@example.com"


async def test_login_wrong_password(client, make_user, db):
    make_user(email="a@example.com", password="Pass!1234567"); db.flush()
    r = await client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong"})
    assert r.status_code == 401


async def test_login_missing_user(client, db):
    r = await client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert r.status_code == 401


async def test_me_falls_back_to_default_user(client):
    # Login is disabled: with no session, /me resolves to the default account
    # (auto-created when the users table is empty) instead of returning 401.
    r = await client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "demo@pallisade.local"


async def test_me_with_session(client, make_user, db):
    make_user(email="a@example.com", password="Pass!1234567"); db.flush()
    await client.post("/api/auth/login", json={"email": "a@example.com", "password": "Pass!1234567"})
    r = await client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


async def test_logout_clears_cookie(client, make_user, db):
    make_user(email="a@example.com", password="Pass!1234567"); db.flush()
    await client.post("/api/auth/login", json={"email": "a@example.com", "password": "Pass!1234567"})
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    # Login is disabled: clearing the session no longer locks you out; /me now
    # falls back to a default account (200) instead of returning 401.
    me = await client.get("/api/auth/me")
    assert me.status_code == 200


async def test_change_password_then_login_with_new(client, make_user, db):
    make_user(email="a@example.com", password="OldPass!12345", must_change=True); db.flush()
    await client.post("/api/auth/login", json={"email": "a@example.com", "password": "OldPass!12345"})
    r = await client.post("/api/auth/change-password",
                          json={"current_password": "OldPass!12345", "new_password": "NewPass!67890"})
    assert r.status_code == 204
    await client.post("/api/auth/logout")
    r2 = await client.post("/api/auth/login",
                           json={"email": "a@example.com", "password": "NewPass!67890"})
    assert r2.status_code == 200
    assert r2.json()["must_change_password"] is False
