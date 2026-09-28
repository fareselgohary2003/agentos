from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import Agent
from app.core.database import get_db
from app.core.deps import get_current_user
from app.evaluation.models import LLMUsage
from app.execution.models import WorkflowExecution
from app.iam.models import User

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/summary")
async def monitoring_summary(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    org_id = current_user.organization_id
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    active_agents = (await db.execute(
        select(func.count()).select_from(Agent).where(
            Agent.organization_id == org_id, Agent.status == "active"
        )
    )).scalar_one()

    total_executions = (await db.execute(
        select(func.count()).select_from(WorkflowExecution).where(
            WorkflowExecution.organization_id == org_id
        )
    )).scalar_one()

    running_executions = (await db.execute(
        select(func.count()).select_from(WorkflowExecution).where(
            WorkflowExecution.organization_id == org_id,
            WorkflowExecution.status.in_(["queued", "executing", "verifying", "replanning"]),
        )
    )).scalar_one()

    done = (await db.execute(
        select(func.count()).select_from(WorkflowExecution).where(
            WorkflowExecution.organization_id == org_id, WorkflowExecution.status == "done"
        )
    )).scalar_one()
    failed = (await db.execute(
        select(func.count()).select_from(WorkflowExecution).where(
            WorkflowExecution.organization_id == org_id, WorkflowExecution.status == "failed"
        )
    )).scalar_one()
    success_rate = round(done / (done + failed), 4) if (done + failed) > 0 else None

    usage_24h = (await db.execute(
        select(
            func.coalesce(func.sum(LLMUsage.total_tokens), 0),
            func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0),
            func.coalesce(func.avg(LLMUsage.latency_ms), 0.0),
        ).where(LLMUsage.organization_id == org_id, LLMUsage.created_at >= since_24h)
    )).one()

    return {
        "active_agents": active_agents,
        "running_workflows": running_executions,
        "total_executions": total_executions,
        "success_rate": success_rate,
        "tokens_24h": int(usage_24h[0]),
        "estimated_cost_24h_usd": round(float(usage_24h[1]), 4),
        "avg_latency_ms_24h": round(float(usage_24h[2]), 2),
    }


@router.get("/cost-by-model")
async def cost_by_model(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(LLMUsage.provider, LLMUsage.model, func.sum(LLMUsage.estimated_cost_usd),
               func.sum(LLMUsage.total_tokens))
        .where(LLMUsage.organization_id == current_user.organization_id)
        .group_by(LLMUsage.provider, LLMUsage.model)
    )
    return [
        {"provider": p, "model": m, "cost_usd": round(float(cost), 4), "tokens": int(tokens)}
        for p, m, cost, tokens in result.all()
    ]
