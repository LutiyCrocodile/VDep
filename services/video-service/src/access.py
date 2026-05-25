from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import Video, VideoUserAccess
from .http_client import get_http_client

CLASSIFICATION_LEVELS = ["public", "internal", "confidential", "restricted"]


async def check_private_video_permission(viewer_id: str, owner_id: str) -> bool:
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/internal/users/{viewer_id}/permissions",
            headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
        )
        if response.status_code == 200:
            permissions = response.json()
            return "video:view_private" in permissions or "view_private_videos" in permissions
    except httpx.RequestError:
        pass
    return False


async def get_user_classification_level(user_id: Optional[str]) -> str:
    if not user_id:
        return "public"

    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/internal/users/{user_id}/services/video",
            headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
        )
        if response.status_code == 200:
            data = response.json()
            role = (data.get("role") or "").lower()
            if role in ("admin", "manager"):
                return "restricted"
            if role in ("uploader", "moderator"):
                return "confidential"
            if role == "viewer":
                return "internal"
    except httpx.RequestError:
        pass

    return "internal"


def can_access_classification(user_level: str, video_level: str) -> bool:
    user_idx = CLASSIFICATION_LEVELS.index(user_level) if user_level in CLASSIFICATION_LEVELS else 0
    video_idx = CLASSIFICATION_LEVELS.index(video_level) if video_level in CLASSIFICATION_LEVELS else 0
    return user_idx >= video_idx


async def user_can_view_video(db: AsyncSession, video: Video, user_id: str) -> bool:
    if str(video.user_id) == user_id:
        return True
    if await VideoUserAccess.check_access(db, str(video.id), user_id):
        return True
    if video.classification == "restricted":
        return False
    if video.is_private:
        return await check_private_video_permission(user_id, str(video.user_id))
    user_level = await get_user_classification_level(user_id)
    return can_access_classification(user_level, video.classification or "public")


async def enforce_video_view_access(db: AsyncSession, video: Video, user_id: str) -> None:
    if not await user_can_view_video(db, video, user_id):
        if video.classification == "restricted" and not await VideoUserAccess.check_access(
            db, str(video.id), user_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Access denied: no explicit access to restricted video",
            )
        if video.is_private:
            raise HTTPException(status_code=403, detail="Access denied: private video")
        raise HTTPException(status_code=403, detail="Access denied: insufficient classification level")
