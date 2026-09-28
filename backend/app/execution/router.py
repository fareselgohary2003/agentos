import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.execution.models import Task, TaskExecution, Workflow, WorkflowExecution
from app.iam.models import User

router = APIRouter(tags=["workflows"])


class WorkflowCreate(BaseModel):
    name: str
    definition: dict = {}


class ExecuteRequest(BaseModel):
    goal: str


def _serialize_workflow(w: Workflow) -> dict:
    return {"id": str(w.id), "name": w.name, "definition": w.definition,
            "created_at": w.created_at.isoformat()}


def _serialize_execution(e: WorkflowExecution) -> dict:
    return {
        "id": str(e.id), "workflow_id": str(e.workflow_id) if e.workflow_id else None,
        "goal": e.goal, "status": e.status, "plan": e.plan,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "finished_at": e.finished_at.isoformat() if e.finished_at else None,
        "error": e.error, "created_at": e.created_at.isoformat(),
    }


@router.get("/api/workflows")
async def list_workflows(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Workflow).where(Workflow.organization_id == current_user.organization_id))
    return [_serialize_workflow(w) for w in result.scalars().all()]


@router.post("/api/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    current_user: User = Depends(require_permission("agents:manage")),
    db: AsyncSession = Depends(get_db),
):
    workflow = Workflow(
        organization_id=current_user.organization_id, name=payload.name,
        definition=payload.definition, created_by=current_user.id,
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return _serialize_workflow(workflow)


@router.get("/api/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None or workflow.organization_id != current_user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    return _serialize_workflow(workflow)


@router.post("/api/workflows/{workflow_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_workflow(
    workflow_id: uuid.UUID,
    payload: ExecuteRequest,
    current_user: User = Depends(require_permission("workflows:execute")),
    db: AsyncSession = Depends(get_db),
):
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None or workflow.organization_id != current_user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")

    execution = WorkflowExecution(
        organization_id=current_user.organization_id, workflow_id=workflow.id,
        user_id=current_user.id, goal=payload.goal, status="queued",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Long-running work never happens on the request thread — hand off to
    # Celery and return immediately (spec §34). Import kept local so the API
    # process doesn't need a broker connection just to boot.
    from app.workers.tasks import execute_workflow_task
    execute_workflow_task.delay(str(execution.id))

    return {"execution_id": str(execution.id), "status": "queued"}


@router.post("/api/goals/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_ad_hoc_goal(
    payload: ExecuteRequest,
    current_user: User = Depends(require_permission("workflows:execute")),
    db: AsyncSession = Depends(get_db),
):
    """Runs the Supervisor directly on a free-form goal with no saved Workflow —
    what the chat-style 'submit a complex goal' UX in spec §1 actually calls."""
    execution = WorkflowExecution(
        organization_id=current_user.organization_id, workflow_id=None,
        user_id=current_user.id, goal=payload.goal, status="queued",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    from app.workers.tasks import execute_workflow_task
    execute_workflow_task.delay(str(execution.id))

    return {"execution_id": str(execution.id), "status": "queued"}


@router.get("/api/executions")
async def list_executions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.organization_id == current_user.organization_id)
        .order_by(WorkflowExecution.created_at.desc())
        .limit(100)
    )
    return [_serialize_execution(e) for e in result.scalars().all()]


@router.get("/api/executions/{execution_id}")
async def get_execution(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    execution = await db.get(WorkflowExecution, execution_id)
    if execution is None or execution.organization_id != current_user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")

    tasks_result = await db.execute(select(Task).where(Task.workflow_execution_id == execution.id))
    tasks = tasks_result.scalars().all()
    task_payloads = []
    for t in tasks:
        te_result = await db.execute(
            select(TaskExecution).where(TaskExecution.task_id == t.id)
        )
        task_executions = te_result.scalars().all()
        task_payloads.append({
            "id": t.external_id, "agent": t.agent, "description": t.description,
            "status": t.status, "dependencies": t.dependencies,
            "executions": [
                {"status": te.status, "output": te.output, "error": te.error,
                 "tool_calls": te.tool_calls}
                for te in task_executions
            ],
        })

    payload = _serialize_execution(execution)
    payload["tasks"] = task_payloads
    return payload
