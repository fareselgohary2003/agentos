import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.models import ApprovalRequest, ApprovalStatus


class ApprovalError(Exception):
    pass


async def create_approval_request(
    db: AsyncSession,
    organization_id: uuid.UUID,
    workflow_execution_id: str,
    task_id: str,
    action: str,
    payload: dict,
    risk_level: str,
    requested_by_agent: str,
) -> ApprovalRequest:
    approval = ApprovalRequest(
        organization_id=organization_id,
        workflow_execution_id=workflow_execution_id,
        task_id=task_id,
        action=action,
        payload=payload,
        risk_level=risk_level,
        requested_by_agent=requested_by_agent,
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    return approval


async def decide_approval(
    db: AsyncSession,
    organization_id: uuid.UUID,
    approval_id: uuid.UUID,
    decided_by_user_id: uuid.UUID,
    approve: bool,
) -> ApprovalRequest:
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == organization_id,  # tenant isolation
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise ApprovalError("Approval request not found")
    if approval.status != ApprovalStatus.PENDING.value:
        raise ApprovalError(f"Approval already decided: {approval.status}")

    approval.status = ApprovalStatus.APPROVED.value if approve else ApprovalStatus.REJECTED.value
    approval.decided_by_user_id = decided_by_user_id
    approval.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(approval)

    # Genuinely resumes the paused LangGraph run from its Postgres checkpoint —
    # see app/workers/tasks.py:resume_workflow_after_approval_task, proven with
    # a real two-process pause/resume test (docs/architecture/00-design.md §8).
    from app.workers.tasks import resume_workflow_after_approval_task
    resume_workflow_after_approval_task.delay(approval.workflow_execution_id, approve)

    return approval


async def list_pending_for_org(db: AsyncSession, organization_id: uuid.UUID) -> list[ApprovalRequest]:
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.organization_id == organization_id,
            ApprovalRequest.status == ApprovalStatus.PENDING.value,
        )
    )
    return list(result.scalars().all())
