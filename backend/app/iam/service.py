import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.iam.models import AuditLog, Organization, Permission, RefreshToken, Role, User
from app.iam.rbac import PERMISSIONS, ROLE_PERMISSIONS
from app.iam.schemas import LoginRequest, RegisterRequest, TokenPair

settings = get_settings()


class AuthError(Exception):
    pass


async def ensure_global_permissions(db: AsyncSession) -> dict[str, Permission]:
    result = await db.execute(select(Permission))
    existing = {p.code: p for p in result.scalars().all()}
    for code, description in PERMISSIONS:
        if code not in existing:
            perm = Permission(code=code, description=description)
            db.add(perm)
            existing[code] = perm
    await db.flush()
    return existing


async def seed_roles_for_organization(db: AsyncSession, organization: Organization) -> dict[str, Role]:
    permissions = await ensure_global_permissions(db)
    roles: dict[str, Role] = {}
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role = Role(organization_id=organization.id, name=role_name, is_system=True)
        role.permissions = [permissions[code] for code in perm_codes]
        db.add(role)
        roles[role_name] = role
    await db.flush()
    return roles


async def register_organization_and_owner(db: AsyncSession, payload: RegisterRequest) -> User:
    existing_slug = await db.execute(
        select(Organization).where(Organization.slug == payload.organization_slug)
    )
    if existing_slug.scalar_one_or_none():
        raise AuthError("Organization slug already taken")

    organization = Organization(name=payload.organization_name, slug=payload.organization_slug)
    db.add(organization)
    await db.flush()

    roles = await seed_roles_for_organization(db, organization)

    user = User(
        organization_id=organization.id,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    user.roles = [roles["OWNER"]]
    db.add(user)
    await db.flush()

    db.add(
        AuditLog(
            organization_id=organization.id,
            user_id=user.id,
            action="user.register",
            resource=f"user:{user.id}",
            log_metadata={"role": "OWNER"},
        )
    )
    await db.commit()
    user.roles = [roles["OWNER"]]  # keep in-memory relation populated post-commit for the caller
    return user


async def authenticate(db: AsyncSession, payload: LoginRequest) -> User:
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.email == payload.email.lower())
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise AuthError("Invalid email or password")
    return user


async def issue_tokens(db: AsyncSession, user: User) -> TokenPair:
    role_names = [r.name for r in user.roles]
    access = create_access_token(user.id, user.organization_id, role_names)
    refresh = create_refresh_token(user.id)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_password(refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action="auth.login",
            resource=f"user:{user.id}",
            log_metadata={},
        )
    )
    await db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise AuthError("Invalid refresh token") from exc
    if payload.get("type") != "refresh":
        raise AuthError("Invalid token type")

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthError("User not found or inactive")

    return await issue_tokens(db, user)


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    )
    now = datetime.now(timezone.utc)
    for token in result.scalars().all():
        token.revoked_at = now
    await db.commit()
