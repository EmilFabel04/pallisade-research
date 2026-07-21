from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from pallisade_connections.crypto import EncryptionUnavailable, decrypt, encrypt
from pallisade_connections.models import DataConnection
from pallisade_connections.registry import CONNECTOR_REGISTRY, get_connector
from pallisade_core.users.models import User
from web.api.deps import get_current_user, get_db, require_admin

router = APIRouter(tags=["connections"])


class ConnectionCreate(BaseModel):
    connector_type: str
    label: str
    credentials: str | None = None
    config: dict = {}
    serves: list[str] = []


class ConnectionUpdate(BaseModel):
    label: str | None = None
    credentials: str | None = None
    config: dict | None = None
    serves: list[str] | None = None


def _view(c: DataConnection) -> dict:
    return {
        "id": str(c.id),
        "connector_type": c.connector_type,
        "label": c.label,
        "status": c.status,
        "credentials_set": c.credentials_encrypted is not None,
        "config": c.config_json or {},
        "serves": list(c.serves or []),
        "last_error": c.last_error,
    }


def _owned(db: Session, cid: uuid.UUID, user: User) -> DataConnection:
    row = db.get(DataConnection, cid)
    if row is None or row.org_id != user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return row


@router.get("/catalog")
def catalog(_: User = Depends(get_current_user)) -> list[dict]:
    return [
        {
            "type_id": c.type_id,
            "requires_credentials": c.requires_credentials,
            "config_fields": c.config_fields,
            "capabilities": sorted(c.capabilities),
        }
        for c in CONNECTOR_REGISTRY.values()
    ]


@router.get("")
def list_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    rows = db.execute(
        select(DataConnection).where(DataConnection.org_id == user.org_id)
        .order_by(DataConnection.created_at)
    ).scalars().all()
    return [_view(r) for r in rows]


@router.post("", status_code=201)
def create_connection(body: ConnectionCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_admin)) -> dict:
    if body.connector_type not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=400, detail="unknown connector_type")
    enc = None
    if body.credentials:
        try:
            enc = encrypt(body.credentials)
        except EncryptionUnavailable as e:
            raise HTTPException(status_code=503, detail=str(e))
    row = DataConnection(
        org_id=user.org_id, connector_type=body.connector_type, label=body.label,
        status="disconnected", credentials_encrypted=enc, config_json=body.config,
        serves=body.serves, created_by=user.id,
    )
    db.add(row)
    db.flush()
    db.commit()
    return _view(row)


@router.patch("/{cid}")
def update_connection(cid: uuid.UUID, body: ConnectionUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_admin)) -> dict:
    row = _owned(db, cid, user)
    if body.label is not None:
        row.label = body.label
    if body.config is not None:
        row.config_json = body.config
    if body.serves is not None:
        row.serves = body.serves
    if body.credentials is not None:
        try:
            row.credentials_encrypted = encrypt(body.credentials) if body.credentials else None
        except EncryptionUnavailable as e:
            raise HTTPException(status_code=503, detail=str(e))
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    db.commit()
    return _view(row)


@router.post("/{cid}/test")
def test_connection(cid: uuid.UUID, db: Session = Depends(get_db),
                    user: User = Depends(require_admin)) -> dict:
    row = _owned(db, cid, user)
    connector = get_connector(row.connector_type)
    try:
        creds = decrypt(row.credentials_encrypted) if row.credentials_encrypted else None
    except EncryptionUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    result = connector.test(creds, row.config_json or {})
    row.status = "connected" if result["ok"] else "error"
    row.last_error = None if result["ok"] else result["detail"]
    row.last_tested_at = datetime.now(timezone.utc)
    db.flush()
    db.commit()
    return {"status": row.status, "result": result}


@router.delete("/{cid}", status_code=204)
def delete_connection(cid: uuid.UUID, db: Session = Depends(get_db),
                      user: User = Depends(require_admin)) -> None:
    row = _owned(db, cid, user)
    db.delete(row)
    db.flush()
    db.commit()
