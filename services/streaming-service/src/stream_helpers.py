"""Stream response builders and auth lookups."""
from __future__ import annotations

import logging
from typing import Optional, Set

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import (
    Stream,
    get_channel_for_owner,
    get_stream_likes_count,
    get_video_likes_count,
    user_liked_stream,
    user_liked_video,
)
from .http_client import get_http_client
from .presence import count_viewers
from .schemas import StreamDetailResponse, StreamResponse

logger = logging.getLogger(__name__)

def mediamtx_path(rtmp_key: str) -> str:
    return f"{settings.rtmp_app}/{rtmp_key}"


def build_public_hls(mediamtx_path: str) -> str:
    return f"{settings.public_hls_base.rstrip('/')}/{mediamtx_path}/index.m3u8"


def build_rtmp_server_url() -> str:
    return f"rtmp://{settings.public_rtmp_host}:{settings.public_rtmp_port}/{settings.rtmp_app}"


def to_stream_response(s: Stream) -> StreamResponse:
    path = getattr(s, "mediamtx_path", None) or mediamtx_path(s.rtmp_key)
    hls = build_public_hls(path)
    vis = getattr(s, "visibility", None) or ("private" if s.is_private else "dgi_employees")
    return StreamResponse(
        id=str(s.id),
        title=s.title,
        description=s.description,
        rtmp_key=s.rtmp_key,
        hls_url=hls,
        is_live=bool(s.is_live),
        start_time=s.start_time,
        end_time=s.end_time,
        user_id=str(s.user_id),
        visibility=vis,
        save_recording=stream_saves_recording(s),
        rtmp_server_url=build_rtmp_server_url(),
        rtmp_stream_key=s.rtmp_key,
    )


def stream_saves_recording(stream: Stream) -> bool:
    val = getattr(stream, "save_recording", None)
    if val is None:
        return True
    return bool(val)


async def stream_likes_state(
    db: AsyncSession, stream: Stream, viewer_id: Optional[str]
) -> tuple[int, bool]:
    if stream.archived_video_id:
        vid = str(stream.archived_video_id)
        count = await get_video_likes_count(db, vid)
        liked = await user_liked_video(db, vid, viewer_id) if viewer_id else False
        return count, liked
    sid = str(stream.id)
    count = await get_stream_likes_count(db, sid)
    liked = await user_liked_stream(db, sid, viewer_id) if viewer_id else False
    return count, liked


async def build_stream_detail(
    db: AsyncSession,
    stream: Stream,
    profile: Optional[dict],
) -> StreamDetailResponse:
    viewer_id = str(profile["id"]) if profile else None
    likes_count, user_liked = await stream_likes_state(db, stream, viewer_id)
    names = await resolve_owner_usernames({str(stream.user_id)})
    base = to_stream_response(stream)
    channel_id, channel_handle = await get_channel_for_owner(db, str(stream.user_id))
    detail = base.model_dump()
    detail.update(
        {
            "owner_username": names.get(str(stream.user_id)),
            "created_at": stream.created_at,
            "likes_count": likes_count,
            "user_liked": user_liked,
            "viewers_count": count_viewers(str(stream.id)),
            "channel_id": channel_id,
            "channel_handle": channel_handle,
            "archived_video_id": str(stream.archived_video_id) if stream.archived_video_id else None,
        }
    )
    return StreamDetailResponse(**detail)


def rtmp_key_from_mediamtx_path(path: str) -> str:
    path = (path or "").strip("/")
    parts = path.split("/")
    return parts[-1] if parts else ""


async def resolve_owner_usernames(user_ids: Set[str]) -> dict:
    """Логины владельцев эфиров по user_id (внутренний вызов auth-service)."""
    if not user_ids:
        return {}
    headers = {"Authorization": f"Bearer {settings.internal_auth_token}"}
    out: dict = {}
    client = get_http_client()
    for uid in user_ids:
        uid_s = str(uid)
        try:
            r = await client.get(
                f"{settings.auth_service_url}/internal/users/{uid_s}/profile-mini",
                headers=headers,
            )
            if r.status_code == 200:
                out[uid_s] = r.json().get("username") or "user"
            else:
                out[uid_s] = "…"
        except httpx.RequestError:
            out[uid_s] = "…"
    return out
