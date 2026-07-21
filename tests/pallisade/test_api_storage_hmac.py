from __future__ import annotations

import io
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from pallisade_core.storage.backend import sign_url_token
from pallisade_core.storage.local_disk import LocalDiskStorage
from web.api.routers.storage import router as storage_router


@pytest.fixture()
async def app_with_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PALLISADE_STORAGE_ROOT", str(tmp_path))
    from pallisade_core import settings as s
    s.get_settings.cache_clear()
    storage = LocalDiskStorage(root=str(tmp_path))
    storage.put("hello.txt", io.BytesIO(b"world"), content_type="text/plain")
    app = FastAPI()
    app.include_router(storage_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_valid_signature(app_with_file):
    c = app_with_file
    exp = int(time.time()) + 60
    sig = sign_url_token("hello.txt", exp=exp)
    r = await c.get(f"/storage/hello.txt?sig={sig}&exp={exp}")
    assert r.status_code == 200
    assert r.content == b"world"


async def test_expired(app_with_file):
    c = app_with_file
    exp = int(time.time()) - 5
    sig = sign_url_token("hello.txt", exp=exp)
    r = await c.get(f"/storage/hello.txt?sig={sig}&exp={exp}")
    assert r.status_code == 403


async def test_tampered(app_with_file):
    c = app_with_file
    exp = int(time.time()) + 60
    sig = sign_url_token("hello.txt", exp=exp)
    r = await c.get(f"/storage/hello.txt?sig={sig[:-2]}xx&exp={exp}")
    assert r.status_code == 403


async def test_missing(app_with_file):
    c = app_with_file
    exp = int(time.time()) + 60
    sig = sign_url_token("nope.txt", exp=exp)
    r = await c.get(f"/storage/nope.txt?sig={sig}&exp={exp}")
    assert r.status_code == 404
