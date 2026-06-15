from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.models import UserRole
from app.db.session import get_db
from app.core.auth_client import auth_client

ACCESS_TOKEN_COOKIE_NAME = "support_access_token"
REFRESH_TOKEN_COOKIE_NAME = "support_refresh_token"


def _extract_bearer(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def _map_support_role(service_role: str | None) -> UserRole:
    role = (service_role or "").lower().strip()
    if role == "admin":
        return UserRole.admin
    if role in ("agent", "moderator"):
        return UserRole.engineer
    return UserRole.user


async def _ensure_local_user(db: AsyncSession, auth_user: dict, service_role: str | None) -> User:
    import uuid as uuid_mod
    from sqlalchemy import select

    username = (auth_user.get("username") or "").strip()
    if not username:
        raise HTTPException(status_code=401, detail="Invalid auth profile")

    auth_id_str = str(auth_user.get("id") or "").strip()
    if not auth_id_str:
        raise HTTPException(status_code=401, detail="Invalid auth profile")

    try:
        auth_id = uuid_mod.UUID(auth_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid auth profile")

    result = await db.execute(select(User).filter(User.id == auth_id))
    user = result.scalar_one_or_none()
    mapped_role = _map_support_role(service_role)

    if user is None:
        user = User(
            id=auth_id,
            username=username,
            full_name=auth_user.get("full_name") or username,
            role=mapped_role,
            is_active=auth_user.get("is_active", True),
            needs_approval=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    user.full_name = auth_user.get("full_name") or user.full_name or username
    user.role = mapped_role
    user.is_active = auth_user.get("is_active", True)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = _extract_bearer(request) or request.cookies.get(ACCESS_TOKEN_COOKIE_NAME) or request.query_params.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_user = await auth_client.verify_token(token)
    if not auth_user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    service_access = await auth_client.get_service_access(auth_user.get("id"))
    service_role = (service_access or {}).get("role")
    user = await _ensure_local_user(db, auth_user, service_role)
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    try:
        if user.role == UserRole.admin:
            from sqlalchemy import select
            result = await db.execute(select(User).filter(User.needs_approval == True))
            request.state.pending_registrations = len(result.scalars().all())
    except Exception:
        pass

    return user


async def get_current_user_optional(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    """Optional version of get_current_user - returns None if not authenticated."""
    token = _extract_bearer(request) or request.cookies.get(ACCESS_TOKEN_COOKIE_NAME) or request.query_params.get("access_token")
    if not token:
        return None

    auth_user = await auth_client.verify_token(token)
    if not auth_user:
        return None

    service_access = await auth_client.get_service_access(auth_user.get("id"))
    user = await _ensure_local_user(db, auth_user, (service_access or {}).get("role"))
    if not user or not user.is_active:
        return None

    try:
        if user.role == UserRole.admin:
            from sqlalchemy import select
            result = await db.execute(select(User).filter(User.needs_approval == True))
            request.state.pending_registrations = len(result.scalars().all())
    except Exception:
        pass

    return user


def require_role(*roles: UserRole):
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _dep
