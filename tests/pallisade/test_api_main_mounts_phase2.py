"""Test that Phase 2 routers are mounted in main.py."""
from __future__ import annotations


def test_phase2_routers_are_registered():
    """Verify documents, retrieve, chat, and library routers are mounted."""
    from web.api.main import app

    # Use the OpenAPI schema rather than iterating app.routes: starlette >=3.4
    # wraps included sub-routers in _IncludedRouter objects that have no .path.
    paths = set(app.openapi()["paths"])
    assert any("/api/deals/{deal_id}/documents" in p for p in paths)
    assert any("/api/deals/{deal_id}/retrieve" in p for p in paths)
    assert any("/api/deals/{deal_id}/chat" in p for p in paths)
    assert any("/api/library/documents" in p for p in paths)
    assert any("/api/library/tickers" in p for p in paths)
