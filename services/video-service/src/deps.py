import hashlib
import logging
from typing import Optional

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from minio import Minio

from .celery_app import celery_app
from .config import settings
from .http_client import get_http_client

logger = logging.getLogger(__name__)

minio_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

security = HTTPBearer(auto_error=False)
internal_bearer = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not credentials:
        return None
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if response.status_code == 200:
            return response.json()["id"]
        return None
    except httpx.RequestError:
        return None


async def require_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    from .auth_client import auth_client

    user_data = await auth_client.verify_token(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    permissions = await auth_client.get_user_service_permissions(user_data["id"])
    if not permissions or not permissions.get("permissions"):
        raise HTTPException(status_code=403, detail="No access to video service")

    return user_data["id"]


async def get_current_user_with_permissions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token required")

    from .auth_client import auth_client

    user_data = await auth_client.verify_token(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    permissions = await auth_client.get_user_service_permissions(user_data["id"])
    if not permissions or not permissions.get("permissions"):
        raise HTTPException(status_code=403, detail="No access to video service")

    return {
        "id": user_data["id"],
        "username": user_data["username"],
        "permissions": permissions.get("permissions", []),
    }


def require_permission(permission: str):
    async def dependency(user=Depends(get_current_user_with_permissions)):
        if permission not in user["permissions"]:
            raise HTTPException(status_code=403, detail=f"Permission '{permission}' required")
        return user["id"]

    return dependency


async def require_internal_token(
    credentials: HTTPAuthorizationCredentials = Depends(internal_bearer),
):
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Invalid internal token")
    return True


def generate_minio_key(video_id: str, filename: str) -> str:
    file_hash = hashlib.sha256(f"{video_id}{filename}".encode()).hexdigest()[:16]
    return f"{video_id}/{file_hash}"


def start_transcoding(video_id: str, minio_key: str):
    celery_app.send_task(
        "src.tasks.transcode_video",
        args=[video_id, minio_key],
        queue="video_transcoding",
    )


def parse_duration(duration_val) -> Optional[int]:
    if not duration_val:
        return None
    if isinstance(duration_val, int):
        return duration_val
    if isinstance(duration_val, str):
        return int(duration_val.rstrip("s"))
    if hasattr(duration_val, "total_seconds"):
        return int(duration_val.total_seconds())
    return None
