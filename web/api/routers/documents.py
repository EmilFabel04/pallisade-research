from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from pallisade_core.deals import service as deals_service
from pallisade_core.documents import service as docs_service
from pallisade_core.documents.models import Document
from pallisade_core.documents.parsers.detect import (
    SourceKind, UnsupportedType, classify_bytes, classify_pdf_text_density,
)
from pallisade_core.documents.parsers.pdf_text import extract_text_pages
from pallisade_core.settings import get_settings
from pallisade_core.users.models import User
from web.api.deps import get_current_user, get_db

router = APIRouter(tags=["documents"])


def _load_deal(db: Session, deal_id: uuid.UUID, me: User):
    deal = deals_service.get_deal(db, deal_id)
    if deal is None or not deals_service.can_view(db, viewer=me, deal=deal):
        raise HTTPException(404, "deal not found")
    return deal


def _serialize(doc: Document) -> dict:
    return {
        "id": str(doc.id),
        "deal_id": str(doc.deal_id),
        "filename": doc.filename,
        "content_type": doc.content_type,
        "byte_size": doc.byte_size,
        "source_kind": doc.source_kind,
        "status": doc.status,
        "page_count": doc.page_count,
        "error_message": doc.error_message,
        "uploader_id": str(doc.uploader_id),
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }


@router.get("/deals/{deal_id}/documents")
def list_documents(deal_id: uuid.UUID, db: Session = Depends(get_db),
                   me: User = Depends(get_current_user)):
    deal = _load_deal(db, deal_id, me)
    docs = docs_service.list_for_deal(db, deal=deal)
    return {"documents": [_serialize(d) for d in docs]}


@router.post("/deals/{deal_id}/documents", status_code=201)
async def upload_document(
    deal_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    deal = _load_deal(db, deal_id, me)

    raw = await file.read()
    cap_mb = get_settings().max_upload_mb
    if len(raw) > cap_mb * 1024 * 1024:
        raise HTTPException(413, f"file exceeds {cap_mb} MB upload cap")

    try:
        first_pass = classify_bytes(
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            head=raw[:8],
        )
    except UnsupportedType as e:
        raise HTTPException(415, str(e))

    if first_pass == SourceKind.PDF_UNKNOWN:
        pages = extract_text_pages(raw)
        kind = classify_pdf_text_density(
            per_page_chars=[len(t) for _, t in pages[:3]]
        )
        source_kind = kind.value
    else:
        source_kind = first_pass.value

    try:
        doc = docs_service.create_document(
            db, deal=deal, uploader=me,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            data=raw, source_kind=source_kind,
        )
    except docs_service.DuplicateDocument as e:
        raise HTTPException(409, f"document already exists: {e.existing.id}")

    db.commit()
    db.refresh(doc)
    return _serialize(doc)


@router.post("/deals/{deal_id}/documents/{doc_id}/retry", status_code=200)
def retry_document(deal_id: uuid.UUID, doc_id: uuid.UUID,
                   db: Session = Depends(get_db),
                   me: User = Depends(get_current_user)):
    deal = _load_deal(db, deal_id, me)
    doc = docs_service.get_document(db, doc_id)
    if doc is None or doc.deal_id != deal.id or doc.deleted_at is not None:
        raise HTTPException(404, "document not found")
    if doc.status != "failed":
        raise HTTPException(409, "only failed documents can be retried")
    docs_service.retry(db, document=doc)
    db.commit()
    db.refresh(doc)
    return _serialize(doc)


@router.delete("/deals/{deal_id}/documents/{doc_id}", status_code=204)
def delete_document(deal_id: uuid.UUID, doc_id: uuid.UUID,
                    db: Session = Depends(get_db),
                    me: User = Depends(get_current_user)):
    deal = _load_deal(db, deal_id, me)
    doc = docs_service.get_document(db, doc_id)
    if doc is None or doc.deal_id != deal.id or doc.deleted_at is not None:
        raise HTTPException(404, "document not found")
    docs_service.soft_delete(db, document=doc)
    db.commit()
    return Response(status_code=204)
