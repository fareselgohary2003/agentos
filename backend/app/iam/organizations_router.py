from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.iam.models import Organization, User
from app.iam.schemas import OrganizationOut

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("/me", response_model=OrganizationOut)
async def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Deliberately fetched via the user's own organization_id, never a client-supplied id,
    # so there is no path by which a user can request another tenant's organization.
    org = await db.get(Organization, current_user.organization_id)
    return org


@router.patch("/me", response_model=OrganizationOut)
async def update_my_organization(
    name: str,
    current_user: User = Depends(require_permission("org:manage")),
    db: AsyncSession = Depends(get_db),
):
    org = await db.get(Organization, current_user.organization_id)
    org.name = name
    await db.commit()
    await db.refresh(org)
    return org
