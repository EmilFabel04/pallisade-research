from __future__ import annotations

from unittest.mock import Mock

import pytest


@pytest.fixture()
def api(client_for, monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv("PALLISADE_CONNECTIONS_ENC_KEY", Fernet.generate_key().decode())
    from pallisade_core import settings as settings_mod
    settings_mod.get_settings.cache_clear()
    from web.api.routers import connections
    yield client_for([("/api/connections", connections.router)])
    settings_mod.get_settings.cache_clear()


@pytest.mark.anyio
async def test_catalog_lists_connector_types(api):
    async with api as c:
        r = await c.get("/api/connections/catalog")
        assert r.status_code == 200
        types = {t["type_id"] for t in r.json()}
        assert {"mcp", "yfinance", "smartkarma", "holdings"} <= types


@pytest.mark.anyio
async def test_create_masks_credentials(api):
    async with api as c:
        r = await c.post("/api/connections", json={
            "connector_type": "smartkarma", "label": "SK",
            "credentials": "sk-secret", "config": {}, "serves": ["research"],
        })
        assert r.status_code == 201
        body = r.json()
        assert body["credentials_set"] is True
        assert "sk-secret" not in str(body)
        assert "credentials" not in body


@pytest.mark.anyio
async def test_test_endpoint_sets_status(api):
    async with api as c:
        created = (await c.post("/api/connections", json={
            "connector_type": "yfinance", "label": "YF", "config": {}, "serves": ["prices"],
        })).json()
        r = await c.post(f"/api/connections/{created['id']}/test")
        assert r.status_code == 200
        assert r.json()["status"] == "connected"


@pytest.mark.anyio
async def test_create_persists_via_commit(api, db):
    db.commit = Mock(wraps=db.commit)
    async with api as c:
        r = await c.post("/api/connections", json={
            "connector_type": "yfinance", "label": "YF", "config": {}, "serves": ["prices"],
        })
        assert r.status_code == 201
        assert db.commit.called


@pytest.mark.anyio
async def test_malformed_id_returns_422(api):
    async with api as c:
        r = await c.patch("/api/connections/not-a-uuid", json={"label": "x"})
        assert r.status_code == 422


@pytest.mark.anyio
async def test_test_endpoint_returns_503_when_decrypt_key_unavailable(api, monkeypatch):
    # Credentialed row exists, key later removed/rotated -> decrypt() raises
    # EncryptionUnavailable. test_connection must surface a 503, not an
    # uncaught 500 (Fix 1 of the final-review minors).
    from pallisade_connections.crypto import EncryptionUnavailable
    from web.api.routers import connections

    async with api as c:
        created = (await c.post("/api/connections", json={
            "connector_type": "smartkarma", "label": "SK",
            "credentials": "sk-secret", "config": {}, "serves": ["research"],
        })).json()
        assert created["credentials_set"] is True

        def _boom(_blob):
            raise EncryptionUnavailable("encryption key not configured")

        monkeypatch.setattr(connections, "decrypt", _boom)

        r = await c.post(f"/api/connections/{created['id']}/test")
        assert r.status_code == 503
