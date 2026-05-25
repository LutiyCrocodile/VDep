"""FastAPI dependencies (auth, RBAC)."""
from __future__ import annotations

from typing import Optional

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth_client import auth_client
from .config import settings
from .http_client import get_http_client

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json()["id"]
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")


async def get_optional_profile(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
) -> Optional[dict]:
    if not credentials:
        return None
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json()
        return None
    except httpx.RequestError:
        return None


async def get_current_user_with_permissions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token required")
    user_data = await auth_client.verify_token(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    permissions = await auth_client.get_user_service_permissions(user_data["id"])
    if not permissions:
        raise HTTPException(status_code=403, detail="Нет доступа к видеосервису (RBAC)")

    return {
        "id": user_data["id"],
        "username": user_data["username"],
        "permissions": permissions.get("permissions", []),
        "is_employee": user_data.get("is_employee", True),
    }


def require_permission(permission: str):
    async def dependency(user=Depends(get_current_user_with_permissions)):
        if permission not in user["permissions"]:
            raise HTTPException(status_code=403, detail=f"Нужно право: {permission}")
        return user["id"]

    return dependency


async def ensure_channel_exists(owner_id: str) -> None:
    client = get_http_client()
    response = await client.get(
        f"{settings.video_service_url}/internal/channels/by-owner/{owner_id}",
        headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
        timeout=15.0,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=403,
            detail="Сначала создайте канал для запуска трансляции",
        )
