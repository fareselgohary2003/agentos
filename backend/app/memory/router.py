from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.iam.models import User
from app.memory.service import retrieve_relevant_memories, store_memory

router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryCreate(BaseModel):
    scope: str  # short_term | episodic | semantic | organization | user
    content: str
    metadata: dict = {}


class MemoryQuery(BaseModel):
    query: str
    top_k: int = 5


def _serialize(m) -> dict:
    return {"id": str(m.id), "scope": m.scope, "content": m.content,
            "created_at": m.created_at.isoformat()}


@router.post("")
async def create_memory(
    payload: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_scoped_id = current_user.id if payload.scope == "user" else None
    memory = await store_memory(
        db, current_user.organization_id, payload.scope, payload.content,
        user_id=user_scoped_id, metadata=payload.metadata,
    )
    await db.commit()
    return _serialize(memory)


@router.post("/search")
async def search_memory(
    payload: MemoryQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """This is the 'retrieve' half of retrieve->rank->filter->inject (spec §16)
    exposed directly, mainly for debugging what an agent would actually see."""
    memories = await retrieve_relevant_memories(
        db, current_user.organization_id, payload.query,
        user_id=current_user.id, top_k=payload.top_k,
    )
    return [_serialize(m) for m in memories]
