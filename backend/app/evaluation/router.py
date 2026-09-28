from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.evaluation.evaluator import run_evaluation_dataset
from app.evaluation.models import Evaluation
from app.iam.models import User

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


class RunEvaluationRequest(BaseModel):
    dataset_name: str
    agent_name: str = "research_agent"


def _serialize(e: Evaluation) -> dict:
    return {"id": str(e.id), "dataset_name": e.dataset_name, "score": e.score,
            "results": e.results, "created_at": e.created_at.isoformat()}


@router.get("")
async def list_evaluations(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Evaluation)
        .where(Evaluation.organization_id == current_user.organization_id)
        .order_by(Evaluation.created_at.desc())
    )
    return [_serialize(e) for e in result.scalars().all()]


@router.post("/run")
async def run_evaluation(
    payload: RunEvaluationRequest,
    current_user: User = Depends(require_permission("agents:manage")),
    db: AsyncSession = Depends(get_db),
):
    evaluation = await run_evaluation_dataset(
        db, current_user.organization_id, payload.dataset_name, payload.agent_name
    )
    return _serialize(evaluation)
