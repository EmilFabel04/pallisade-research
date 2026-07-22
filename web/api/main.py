"""Pallisade FastAPI app — Phase 1 auth + Phase 2 documents/retrieve/chat."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web.api.routers.auth import router as auth_router
from web.api.routers.chat import router as chat_router
from web.api.routers.connections import router as connections_router
from web.api.routers.documents import router as documents_router
from web.api.routers.export import router as export_router
from web.api.routers.org_documents import router as org_documents_router
from web.api.routers.retrieve import router as retrieve_router
from web.api.routers.runs import router as runs_router
from web.api.routers.library import router as library_router
from web.api.routers.memo_checks import router as memo_checks_router
from web.api.routers.storage import router as storage_router
from web.api.routers.research import router as research_router
from web.api.routers.market import router as market_router
from web.api.routers.watchlist import router as watchlist_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Pallisade Evaluator", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",  # dev: UI fallback port (3000 taken by ledger app)
        "http://localhost:3007", "http://127.0.0.1:3007",  # dev: research-copilot UI port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(runs_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(org_documents_router, prefix="/api")
app.include_router(retrieve_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(memo_checks_router, prefix="/api")
app.include_router(storage_router)
app.include_router(research_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(connections_router, prefix="/api/connections")
app.include_router(market_router, prefix="/api/market")
app.include_router(watchlist_router, prefix="/api/watchlist")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
