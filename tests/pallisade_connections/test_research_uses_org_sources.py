from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def api(client_for):
    from web.api.routers import research
    return client_for([("", research.router)])


@pytest.mark.anyio
async def test_ask_resolves_per_org_without_error(api):
    # Deterministic: verifies the resolver->answer->serialize wiring executes for
    # the current user's org and returns the cited-answer shape. (The "only
    # connected sources / yfinance fallback" behavior is unit-tested in Task 7's
    # resolver tests; this avoids a flaky live-network assertion on yfinance.)
    async with api as c:
        r = await c.post("/research/ask", json={"question": "How is AAPL doing?"})
        assert r.status_code == 200
        body = r.json()
        assert "sources_used" in body
        assert "records" in body
        assert isinstance(body["records"], list)
