"""Every repository for a tenant-owned table MUST extend TenantScopedRepository.

This is the single choke point for tenant isolation: it is structurally
impossible to build a SELECT/UPDATE/DELETE against a tenant table here
without supplying organization_id, because the constructor requires it
and every helper method injects it into the WHERE clause.
"""
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class TenantScopedRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: AsyncSession, organization_id: UUID):
        if organization_id is None:
            raise ValueError("organization_id is required for tenant-scoped repositories")
        self.db = db
        self.organization_id = organization_id

    def _base_query(self):
        return select(self.model).where(self.model.organization_id == self.organization_id)

    async def get(self, id: UUID) -> ModelT | None:
        query = self._base_query().where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        query = self._base_query().limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def add(self, instance: ModelT) -> ModelT:
        if getattr(instance, "organization_id", None) != self.organization_id:
            raise ValueError("Cannot persist an entity outside the current tenant")
        self.db.add(instance)
        await self.db.flush()
        return instance
