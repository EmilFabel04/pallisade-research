from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from pallisade_core.documents.models import Document, DocumentChunk, ProcessingJob
from pallisade_core.documents.parsers import pdf_ocr, pdf_text, xlsx
from pallisade_core.rag.chunking import Chunk, chunk_pages, chunk_sheets
from pallisade_core.storage.local_disk import LocalDiskStorage

log = logging.getLogger(__name__)


@dataclass
class ParseContext:
    """Injectable dependencies — overridable in tests."""
    ocr_client: pdf_ocr.VisionClient | None = None
    storage: LocalDiskStorage | None = None
    ocr_concurrency: int = 4


def _read_bytes(doc: Document, *, storage: LocalDiskStorage | None) -> bytes:
    s = storage or LocalDiskStorage()
    fh = s.get(doc.storage_key)
    try:
        return fh.read()
    finally:
        fh.close()


def handle_parse(
    session: Session, job: ProcessingJob, doc: Document, *, ctx: ParseContext | None = None,
) -> None:
    ctx = ctx or ParseContext()
    doc.status = "parsing"
    session.flush()

    data = _read_bytes(doc, storage=ctx.storage)
    chunks: list[Chunk] = []

    if doc.source_kind == "pdf_text":
        pages = pdf_text.extract_text_pages(data)
        total = sum(len(t) for _, t in pages)
        if total < 100:
            log.info("doc %s text-too-short, re-routing to OCR", doc.id)
            doc.source_kind = "pdf_scan"
            session.flush()
            # fall through into OCR branch below by re-checking source_kind
        else:
            chunks = chunk_pages(pages)
            doc.page_count = len(pages)

    if doc.source_kind == "pdf_scan":
        if ctx.ocr_client is None:
            from pallisade_core.settings import get_settings
            s = get_settings()
            ctx = ParseContext(
                ocr_client=pdf_ocr.AnthropicVisionClient(
                    api_key=s.anthropic_api_key, model=s.ocr_model,
                ),
                storage=ctx.storage,
                ocr_concurrency=s.ocr_concurrency,
            )
        pages = asyncio.run(pdf_ocr.extract_text_pages(
            data=data, client=ctx.ocr_client, concurrency=ctx.ocr_concurrency,
        ))
        total = sum(len(t) for _, t in pages)
        if total < 100:
            raise RuntimeError("OCR produced empty result")
        chunks = chunk_pages(pages)
        doc.page_count = len(pages)
    elif doc.source_kind == "xlsx":
        sheets = xlsx.extract_sheets(data)
        chunks = chunk_sheets(sheets)
        doc.page_count = len(sheets)

    if not chunks:
        raise RuntimeError("no chunks produced")

    for c in chunks:
        session.add(DocumentChunk(
            document_id=doc.id, deal_id=doc.deal_id, org_id=doc.org_id,
            chunk_index=c.chunk_index, text=c.text, token_count=c.token_count,
            page_from=c.page_from, page_to=c.page_to, sheet_name=c.sheet_name,
        ))

    doc.status = "embedding"
    session.add(ProcessingJob(
        job_type="embed_document", document_id=doc.id, status="queued",
    ))
    session.flush()
