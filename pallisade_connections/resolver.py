from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pallisade_connections.crypto import decrypt
from pallisade_connections.models import DataConnection
from pallisade_connections.registry import get_connector
from pallisade_core.documents.models import Document
from pallisade_research.sources.documents import DocumentsSource
from pallisade_research.sources.registry import ClientConfig


@dataclass
class ResolvedSources:
    client_config: ClientConfig
    registry: dict = field(default_factory=dict)
    sources_unavailable: list[str] = field(default_factory=list)


BUILTIN_ALWAYS_ON = ("yfinance", "eodhd", "eodhd_markets", "eodhd_fundamentals", "worldbank")


def resolve_for_org(db: Session, org_id: uuid.UUID) -> ResolvedSources:
    registry: dict = {
        t: get_connector(t).as_research_source(None, {}) for t in BUILTIN_ALWAYS_ON
    }
    unavailable: list[str] = []

    rows = db.execute(
        select(DataConnection).where(
            DataConnection.org_id == org_id,
            DataConnection.status == "connected",
        )
    ).scalars().all()

    for row in rows:
        if row.connector_type in BUILTIN_ALWAYS_ON:
            continue  # already present as a built-in
        try:
            connector = get_connector(row.connector_type)
            creds = decrypt(row.credentials_encrypted) if row.credentials_encrypted else None
            registry[row.connector_type] = connector.as_research_source(creds, row.config_json or {})
        except Exception:  # noqa: BLE001 — a bad connection must not break the whole run
            unavailable.append(row.label)

    has_ready_doc = db.execute(
        select(func.count()).select_from(Document).where(
            Document.org_id == org_id,
            Document.status == "ready",
            Document.deleted_at.is_(None),
        )
    ).scalar_one()
    if has_ready_doc:
        registry["documents"] = DocumentsSource(session=db, org_id=org_id)

    config = ClientConfig(client_id=str(org_id), enabled_sources=frozenset(registry))
    return ResolvedSources(client_config=config, registry=registry, sources_unavailable=unavailable)
