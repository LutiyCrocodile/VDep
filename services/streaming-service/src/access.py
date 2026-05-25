"""Stream visibility and access control."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Stream, is_stream_viewer


def rtmp_session_active(stream: Stream) -> bool:
    """Ожидание OBS или эфир в процессе."""
    if bool(stream.is_live):
        return True
    if stream.end_time is None:
        return True
    return False


def rtmp_ui_state(stream: Stream, archive_phase: str) -> str:
    if archive_phase in ("pending", "waiting_recording", "uploading", "transcoding", "failed"):
        return "archiving"
    if archive_phase == "ready":
        return "archive_ready"
    if stream.is_live:
        return "live"
    if stream.end_time is None:
        return "waiting_obs"
    return "idle"


def can_view_stream(stream: Stream, profile: Optional[dict]) -> bool:
    if not profile:
        return False
    uid = str(profile["id"])
    if str(stream.user_id) == uid:
        return True
    vis = getattr(stream, "visibility", None) or ("private" if stream.is_private else "dgi_employees")
    if vis == "dgi_employees":
        return bool(profile.get("is_employee", True))
    return False


async def can_view_stream_db(db: AsyncSession, stream: Stream, profile: Optional[dict]) -> bool:
    if can_view_stream(stream, profile):
        return True
    if not profile:
        return False
    vis = getattr(stream, "visibility", None) or ("private" if stream.is_private else "dgi_employees")
    if vis == "private":
        return await is_stream_viewer(db, str(stream.id), str(profile["id"]))
    return False


async def require_stream_view_access(
    db: AsyncSession, stream_id: str, profile: Optional[dict]
) -> Stream:
    stream = await Stream.get_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    if not await can_view_stream_db(db, stream, profile):
        raise HTTPException(status_code=403, detail="Нет доступа к трансляции")
    return stream
