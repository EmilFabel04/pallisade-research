from __future__ import annotations

from contextlib import contextmanager
from typing import Annotated

from langchain_core.tools import tool

from pallisade_core.db.session import get_session_factory
from pallisade_core.rag.retrieve import retrieve_passages
from tradingagents.dataflows.config import get_config

_MIN_SCORE = 0.35
_K = 6


def _get_config() -> dict:
    return get_config()


@contextmanager
def _session_scope():
    sf = get_session_factory()
    with sf() as s:
        yield s


def _retriever(session, **kwargs):
    return retrieve_passages(session, **kwargs)


@tool
def search_org_documents(
    query: Annotated[str, "what to look up in the firm's own documents"],
) -> str:
    """Search the firm's own uploaded/synced documents — the highest-priority,
    licensed source. Consult this FIRST. Returns cited passages (filename + page)
    from the organization's private corpus, or a notice if none are available."""
    cfg = _get_config()
    org_id = cfg.get("org_id")
    if not org_id:
        return "No org context — no firm documents available for this run."

    with _session_scope() as session:
        passages = _retriever(session, org_id=org_id, query=query, k=_K)

    strong = [p for p in passages if p.score >= _MIN_SCORE]
    if not strong:
        return "No documents matched this query in the firm's corpus."

    lines = []
    for p in strong:
        page = f" p.{p.page_from}" if p.page_from is not None else ""
        lines.append(f"[{p.filename}{page}] {p.text.strip()}")
    return "\n\n".join(lines)
