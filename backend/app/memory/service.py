"""retrieve -> rank -> filter -> inject.

Memories are never blindly dumped into a prompt (spec §16). This module is
the single place that decides what memory content an agent actually sees.

Ranking here is a simple keyword-overlap score, which is a reasonable,
dependency-free baseline; swap `_score` for a pgvector cosine-similarity
query once document/memory embeddings are populated (Phase 5 hardening —
the `memories` table and RAG's `document_chunks` are the natural place to
add an `embedding` column and an ivfflat index).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Memory


def _score(query: str, content: str) -> float:
    query_terms = set(query.lower().split())
    content_terms = set(content.lower().split())
    if not query_terms:
        return 0.0
    return len(query_terms & content_terms) / len(query_terms)


async def retrieve_relevant_memories(
    db: AsyncSession,
    organization_id: uuid.UUID,
    query: str,
    user_id: uuid.UUID | None = None,
    top_k: int = 5,
    min_score: float = 0.1,
) -> list[Memory]:
    result = await db.execute(
        select(Memory).where(Memory.organization_id == organization_id).limit(500)
    )
    candidates = result.scalars().all()

    # filter: user-scoped memories only for their own user; org/semantic/episodic visible org-wide
    filtered = [
        m for m in candidates
        if m.scope != "user" or m.user_id == user_id
    ]

    # rank
    scored = [(m, _score(query, m.content)) for m in filtered]
    scored = [(m, s) for m, s in scored if s >= min_score]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    return [m for m, _ in scored[:top_k]]


async def store_memory(
    db: AsyncSession,
    organization_id: uuid.UUID,
    scope: str,
    content: str,
    user_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> Memory:
    memory = Memory(
        organization_id=organization_id,
        user_id=user_id,
        scope=scope,
        content=content,
        memory_metadata=metadata or {},
    )
    db.add(memory)
    await db.flush()
    return memory
