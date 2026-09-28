import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import Agent
from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.iam.models import User

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt_ref: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_iterations: int = 8
    allowed_tools: list[str] = []


class AgentUpdate(BaseModel):
    description: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_iterations: int | None = None
    allowed_tools: list[str] | None = None
    status: str | None = None


def _serialize(agent: Agent) -> dict:
    return {
        "id": str(agent.id), "name": agent.name, "description": agent.description,
        "model": agent.model, "temperature": agent.temperature,
        "max_iterations": agent.max_iterations, "allowed_tools": agent.allowed_tools,
        "status": agent.status, "version": agent.version,
    }


@router.get("")
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.organization_id == current_user.organization_id))
    return [_serialize(a) for a in result.scalars().all()]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if agent is None or agent.organization_id != current_user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return _serialize(agent)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    current_user: User = Depends(require_permission("agents:manage")),
    db: AsyncSession = Depends(get_db),
):
    agent = Agent(organization_id=current_user.organization_id, **payload.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _serialize(agent)


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    current_user: User = Depends(require_permission("agents:manage")),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if agent is None or agent.organization_id != current_user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    agent.version += 1
    await db.commit()
    await db.refresh(agent)
    return _serialize(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    current_user: User = Depends(require_permission("agents:manage")),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if agent is None or agent.organization_id != current_user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    await db.delete(agent)
    await db.commit()
