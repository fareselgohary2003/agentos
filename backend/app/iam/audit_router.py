from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permission
from app.iam.models import AuditLog, User

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("")
async def list_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_permission("audit:view")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == current_user.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
    )
    return [
        {
            "id": str(log.id), "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action, "resource": log.resource, "metadata": log.log_metadata,
            "created_at": log.created_at.isoformat(),
        }
        for log in result.scalars().all()
    ]
