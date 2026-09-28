import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals import service
from app.core.database import get_db
from app.core.deps import require_permission
from app.iam.models import User

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("")
async def list_approvals(
    current_user: User = Depends(require_permission("approvals:decide")),
    db: AsyncSession = Depends(get_db),
):
    approvals = await service.list_pending_for_org(db, current_user.organization_id)
    return [
        {
            "id": str(a.id),
            "action": a.action,
            "payload": a.payload,
            "risk_level": a.risk_level,
            "status": a.status,
            "requested_by_agent": a.requested_by_agent,
            "created_at": a.created_at.isoformat(),
        }
        for a in approvals
    ]


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: uuid.UUID,
    current_user: User = Depends(require_permission("approvals:decide")),
    db: AsyncSession = Depends(get_db),
):
    try:
        approval = await service.decide_approval(
            db, current_user.organization_id, approval_id, current_user.id, approve=True
        )
    except service.ApprovalError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"id": str(approval.id), "status": approval.status}


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: uuid.UUID,
    current_user: User = Depends(require_permission("approvals:decide")),
    db: AsyncSession = Depends(get_db),
):
    try:
        approval = await service.decide_approval(
            db, current_user.organization_id, approval_id, current_user.id, approve=False
        )
    except service.ApprovalError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"id": str(approval.id), "status": approval.status}
