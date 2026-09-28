import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.evaluation.models import Document
from app.iam.models import User
from app.rag.service import ingest_document_text, retrieve_and_rerank

router = APIRouter(prefix="/api/documents", tags=["documents", "rag"])


class DocumentIngestRequest(BaseModel):
    title: str
    source: str = "upload"
    text: str


class DocumentSearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("", status_code=status.HTTP_201_CREATED)
async def ingest_document(
    payload: DocumentIngestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    document = Document(
        organization_id=current_user.organization_id, title=payload.title, source=payload.source,
        owner_id=current_user.id, storage_key=f"documents/{uuid.uuid4()}.txt",
        content_preview=payload.text[:500],
    )
    db.add(document)
    await db.flush()
    chunks = await ingest_document_text(db, document, payload.text)
    await db.commit()
    return {"document_id": str(document.id), "chunks_created": len(chunks)}


@router.post("/search")
async def search_documents(
    payload: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chunks = await retrieve_and_rerank(db, current_user.organization_id, payload.query, payload.top_k)
    return [
        {"document_id": str(c.document_id), "chunk_index": c.chunk_index, "content": c.content}
        for c in chunks
    ]
