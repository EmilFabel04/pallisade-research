from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import islice
from typing import Iterable, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from pallisade_core.documents.models import Document, DocumentChunk, ProcessingJob
from pallisade_core.rag.embeddings import Embedder, build_default_embedder, embed_documents

log = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class EmbedContext:
    embedder: Embedder | None = None
    batch_size: int = 128


def _batched(seq: list[T], n: int) -> Iterable[list[T]]:
    it = iter(seq)
    while True:
        batch = list(islice(it, n))
        if not batch:
            return
        yield batch


def handle_embed(
    session: Session, job: ProcessingJob, doc: Document, *, ctx: EmbedContext | None = None,
) -> None:
    ctx = ctx or EmbedContext()
    embedder = ctx.embedder or build_default_embedder()

    chunks = list(session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id, DocumentChunk.embedding.is_(None))
        .order_by(DocumentChunk.chunk_index)
    ).scalars())

    if not chunks:
        doc.status = "ready"
        session.flush()
        return

    for batch in _batched(chunks, ctx.batch_size):
        vectors = embed_documents([c.text for c in batch], embedder=embedder)
        for c, v in zip(batch, vectors):
            c.embedding = v
        session.flush()

    doc.status = "ready"
    session.flush()
