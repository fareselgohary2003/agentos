import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import ToolCatalogEntry
from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.iam.models import User
from app.tools.registry import get_tool_registry

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolUpdate(BaseModel):
    is_enabled: bool | None = None
    timeout_seconds: int | None = None


def _serialize(t: ToolCatalogEntry) -> dict:
    return {
        "id": str(t.id), "name": t.name, "description": t.description,
        "risk_level": t.risk_level, "timeout_seconds": t.timeout_seconds,
        "is_enabled": t.is_enabled, "scope": "organization" if t.organization_id else "global",
    }


@router.get("")
async def list_tools(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Global tools (organization_id IS NULL) plus this org's own overrides."""
    result = await db.execute(
        select(ToolCatalogEntry).where(
            or_(ToolCatalogEntry.organization_id.is_(None),
                ToolCatalogEntry.organization_id == current_user.organization_id)
        )
    )
    catalog = [_serialize(t) for t in result.scalars().all()]
    return {"catalog": catalog, "runtime_registered": get_tool_registry().list_names()}


@router.patch("/{tool_id}")
async def update_tool(
    tool_id: uuid.UUID,
    payload: ToolUpdate,
    current_user: User = Depends(require_permission("tools:manage")),
    db: AsyncSession = Depends(get_db),
):
    tool = await db.get(ToolCatalogEntry, tool_id)
    if tool is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tool not found")
    if tool.organization_id not in (None, current_user.organization_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot modify another organization's tool")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tool, field, value)
    await db.commit()
    await db.refresh(tool)
    return _serialize(tool)
