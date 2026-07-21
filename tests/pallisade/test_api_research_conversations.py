"""API tests for per-user research conversation history."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web.api.deps import get_current_user, get_db
from web.api.routers import research

MSGS = [
    {"id": 1, "role": "user", "content": "overview of AAPL"},
    {"id": 2, "role": "assistant", "content": "Apple is...", "answer": {"claims": []}},
]


@pytest.fixture()
def make_api(db, make_user):
    def _build(user):
        app = FastAPI()
        app.include_router(research.router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    return _build


def test_save_list_get_delete_roundtrip(make_api, make_user):
    user = make_user()
    api = make_api(user)

    # create
    r = api.post("/api/research/conversations", json={"title": "overview of AAPL", "messages": MSGS})
    assert r.status_code == 200
    cid = r.json()["id"]
    assert r.json()["title"] == "overview of AAPL"

    # update (same id → same row)
    r = api.post("/api/research/conversations",
                 json={"id": cid, "title": "overview of AAPL", "messages": MSGS + [{"id": 3, "role": "user", "content": "more?"}]})
    assert r.status_code == 200 and r.json()["id"] == cid

    # list shows exactly one
    r = api.get("/api/research/conversations")
    assert r.status_code == 200 and len(r.json()) == 1

    # get restores full messages
    r = api.get(f"/api/research/conversations/{cid}")
    assert r.status_code == 200
    assert len(r.json()["messages"]) == 3

    # delete
    assert api.delete(f"/api/research/conversations/{cid}").status_code == 204
    assert api.get("/api/research/conversations").json() == []


def test_get_missing_returns_404(make_api, make_user):
    api = make_api(make_user())
    import uuid
    assert api.get(f"/api/research/conversations/{uuid.uuid4()}").status_code == 404


def test_conversations_are_user_isolated(make_api, make_user):
    a, b = make_user(), make_user()
    cid = make_api(a).post("/api/research/conversations", json={"title": "a-conv", "messages": MSGS}).json()["id"]

    api_b = make_api(b)
    assert api_b.get("/api/research/conversations").json() == []   # B sees nothing of A's
    assert api_b.get(f"/api/research/conversations/{cid}").status_code == 404
    assert api_b.delete(f"/api/research/conversations/{cid}").status_code == 404
