"""Upload -> Parse -> Chunk -> Metadata -> Index -> Retrieve -> Rerank -> Agent (spec §17).

Retrieval ranking is keyword-overlap (same approach as app/memory/service.py,
for the same reason: zero extra infra to demo end-to-end). Swap `_score` for
a pgvector cosine-similarity query once `document_chunks.embedding` is
populated by a real embeddings call — the interface below doesn't change.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.evaluation.models import Document

CHUNK_SIZE_CHARS = 800
CHUNK_OVERLAP_CHARS = 100


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def chunk_text(text: str, size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


async def ingest_document_text(
    db: AsyncSession, document: Document, full_text: str
) -> list[DocumentChunk]:
    chunks = []
    for i, piece in enumerate(chunk_text(full_text)):
        chunk = DocumentChunk(
            document_id=document.id, organization_id=document.organization_id,
            chunk_index=i, content=piece, chunk_metadata={"title": document.title},
        )
        db.add(chunk)
        chunks.append(chunk)
    await db.flush()
    return chunks


def _score(query: str, content: str) -> float:
    query_terms = set(query.lower().split())
    content_terms = set(content.lower().split())
    if not query_terms:
        return 0.0
    return len(query_terms & content_terms) / len(query_terms)


async def retrieve_and_rerank(
    db: AsyncSession, organization_id: uuid.UUID, query: str, top_k: int = 5
) -> list[DocumentChunk]:
    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.organization_id == organization_id).limit(1000)
    )
    candidates = result.scalars().all()
    scored = sorted(
        ((c, _score(query, c.content)) for c in candidates), key=lambda p: p[1], reverse=True
    )
    return [c for c, s in scored[:top_k] if s > 0]
