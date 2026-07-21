from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from pallisade_core.deals.models import Deal
from pallisade_core.documents.models import Document, DocumentChunk, ProcessingJob
from pallisade_core.storage.backend import StorageBackend
from pallisade_core.storage.local_disk import LocalDiskStorage
from pallisade_core.users.models import User


class DuplicateDocument(Exception):
    """Raised when (deal_id, sha256) already exists for an active document."""

    def __init__(self, existing: Document):
        self.existing = existing
        if existing.deal_id is not None:
            message = f"document already exists for this deal: {existing.id}"
        elif existing.org_id is not None:
            message = f"document already exists for this org: {existing.id}"
        else:
            message = f"document already exists: {existing.id}"
        super().__init__(message)


def _storage() -> StorageBackend:
    return LocalDiskStorage()


def create_document(
    session: Session, *, deal: Deal, uploader: User,
    filename: str, content_type: str, data: bytes, source_kind: str,
    storage: StorageBackend | None = None,
) -> Document:
    sha = hashlib.sha256(data).hexdigest()

    existing = session.execute(
        select(Document).where(
            Document.deal_id == deal.id,
            Document.sha256 == sha,
            Document.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicateDocument(existing)

    doc = Document(
        deal_id=deal.id, uploader_id=uploader.id,
        filename=filename, storage_key="",  # set after we have the id
        content_type=content_type, byte_size=len(data), sha256=sha,
        source_kind=source_kind, status="pending",
    )
    session.add(doc)
    session.flush()  # populate doc.id

    storage_key = f"deals/{deal.id}/docs/{doc.id}/{filename}"
    (storage or _storage()).put(storage_key, io.BytesIO(data), content_type)
    doc.storage_key = storage_key

    session.add(ProcessingJob(job_type="parse_document", document_id=doc.id, status="queued"))
    return doc


def create_org_document(
    session: Session, *, org_id: uuid.UUID, uploader: User,
    filename: str, content_type: str, data: bytes, source_kind: str,
    storage: StorageBackend | None = None,
) -> Document:
    sha = hashlib.sha256(data).hexdigest()

    existing = session.execute(
        select(Document).where(
            Document.org_id == org_id,
            Document.sha256 == sha,
            Document.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicateDocument(existing)

    doc = Document(
        org_id=org_id, deal_id=None, uploader_id=uploader.id,
        filename=filename, storage_key="",
        content_type=content_type, byte_size=len(data), sha256=sha,
        source_kind=source_kind, status="pending",
    )
    session.add(doc)
    session.flush()

    storage_key = f"orgs/{org_id}/docs/{doc.id}/{filename}"
    (storage or _storage()).put(storage_key, io.BytesIO(data), content_type)
    doc.storage_key = storage_key

    session.add(ProcessingJob(job_type="parse_document", document_id=doc.id, status="queued"))
    return doc


def get_document(session: Session, doc_id) -> Document | None:
    return session.get(Document, doc_id)


def list_for_deal(session: Session, *, deal: Deal) -> list[Document]:
    return list(session.execute(
        select(Document)
        .where(Document.deal_id == deal.id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    ).scalars())


def list_for_org(session: Session, *, org_id) -> list[Document]:
    return list(session.execute(
        select(Document)
        .where(Document.org_id == org_id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    ).scalars())


def soft_delete(session: Session, *, document: Document) -> None:
    document.deleted_at = datetime.now(timezone.utc)


def retry(session: Session, *, document: Document) -> None:
    document.status = "pending"
    document.error_message = None
    session.add(ProcessingJob(
        job_type="parse_document", document_id=document.id, status="queued",
    ))
