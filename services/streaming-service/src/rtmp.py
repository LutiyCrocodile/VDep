"""RTMP / MediaMTX lifecycle and reconcile loop."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import httpx
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from .archive import schedule_archive_if_needed
from .config import settings
from .constants import RTMP_OFFLINE_FINALIZE_AFTER, _rtmp_offline_streak
from .database import Stream, async_session, get_channel_for_owner
from .http_client import get_http_client
from .stream_helpers import mediamtx_path

logger = logging.getLogger(__name__)

async def rtmp_reconcile_loop() -> None:
    """Периодически завершает эфиры без RTMP-публикатора (webhook MediaMTX в образе не работает)."""
    await asyncio.sleep(5)
    while True:
        try:
            async with async_session() as db:
                for stream in await Stream.get_streams_for_rtmp_reconcile(db):
                    await reconcile_stream_rtmp_state(db, stream)
        except Exception:
            logger.exception("RTMP reconcile loop error")
        await asyncio.sleep(10)
async def mediamtx_path_has_publisher(path_name: str) -> Optional[bool]:
    """True — RTMP идёт, False — пути нет, None — API недоступен."""
    encoded = quote(path_name, safe="")
    url = f"{settings.mediamtx_api_url.rstrip('/')}/v3/paths/get/{encoded}"
    try:
        client = get_http_client()
        resp = await client.get(url, timeout=3.0)
        if resp.status_code == 404:
            return False
        if resp.status_code != 200:
            logger.warning("MediaMTX paths/get %s -> %s", path_name, resp.status_code)
            return None
        data = resp.json()
        if data.get("error"):
            return False
        return bool(data.get("ready") or data.get("source"))
    except httpx.RequestError as exc:
        logger.warning("MediaMTX API unreachable: %s", exc)
        return None


async def finalize_stream_session(
    db: AsyncSession,
    stream: Stream,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    if stream.archived_video_id:
        return
    if stream.end_time is not None and not stream.is_live:
        st = getattr(stream, "archive_status", None)
        if st not in ("pending", "waiting_recording", "uploading"):
            return
    await Stream.update_status(db, str(stream.id), is_live=False, end_time=datetime.utcnow())
    await schedule_archive_if_needed(str(stream.id), background_tasks)


async def promote_stream_live_on_rtmp(
    db: AsyncSession,
    stream: Stream,
    *,
    notify: bool = True,
) -> Stream:
    """Эфир идёт в MediaMTX, но в БД ещё не live (webhook runOnReady отключён)."""
    was_already_live = bool(stream.is_live)
    now = datetime.utcnow()
    await Stream.update_status(
        db,
        str(stream.id),
        is_live=True,
        start_time=stream.start_time or now,
    )
    refreshed = await Stream.get_by_id(db, str(stream.id)) or stream
    if notify and refreshed and not was_already_live:
        channel_id, channel_handle = await get_channel_for_owner(db, str(refreshed.user_id))
        if channel_id:
            channel_name = ""
            try:
                client = get_http_client()
                ch = await client.get(
                    f"{settings.video_service_url}/internal/channels/by-owner/{refreshed.user_id}",
                    headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
                    timeout=10.0,
                )
                if ch.status_code == 200:
                    channel_name = ch.json().get("name") or ""
                    channel_handle = ch.json().get("handle") or channel_handle
            except httpx.RequestError:
                pass
            await notify_stream_live(refreshed, channel_id, channel_name, channel_handle)
    return refreshed


async def reconcile_stream_rtmp_state(
    db: AsyncSession,
    stream: Stream,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Stream:
    if stream.end_time is not None:
        return stream

    sid = str(stream.id)
    path = getattr(stream, "mediamtx_path", None) or mediamtx_path(stream.rtmp_key)
    publishing = await mediamtx_path_has_publisher(path)

    if publishing is True:
        _rtmp_offline_streak.pop(sid, None)
        if not stream.is_live:
            logger.info("RTMP reconcile: mark live stream %s (path %s)", stream.id, path)
            return await promote_stream_live_on_rtmp(db, stream)
        return stream

    if publishing is None:
        return stream

    if not stream.is_live and not stream.start_time:
        return stream

    streak = _rtmp_offline_streak.get(sid, 0) + 1
    _rtmp_offline_streak[sid] = streak
    if streak < RTMP_OFFLINE_FINALIZE_AFTER:
        return stream

    _rtmp_offline_streak.pop(sid, None)
    logger.info("RTMP reconcile: finalize stream %s (path %s offline x%s)", stream.id, path, streak)
    await finalize_stream_session(db, stream, background_tasks)
    refreshed = await Stream.get_by_id(db, sid)
    return refreshed or stream


async def notify_stream_live(stream: Stream, channel_id: str, channel_name: str, channel_handle: Optional[str]):
    payload = {
        "event_type": "stream_live",
        "channel_id": channel_id,
        "owner_id": str(stream.user_id),
        "channel_name": channel_name or "",
        "channel_handle": channel_handle,
        "title": stream.title or "Трансляция",
        "entity_id": str(stream.id),
        "link_path": f"/stream/{stream.id}",
    }
    try:
        client = get_http_client()
        r = await client.post(
            f"{settings.notification_service_url}/internal/events/channel",
            json=payload,
            headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
            timeout=20.0,
        )
        if r.status_code != 200:
            logger.warning("stream_live notify failed: %s %s", r.status_code, r.text)
        else:
            logger.info("stream_live notify: %s", r.json())
    except httpx.RequestError as e:
        logger.warning("stream_live notify error: %s", e)


async def mark_stream_live_on_rtmp_publish(db: AsyncSession, rtmp_key: str) -> Optional[Stream]:
    """Разрешить RTMP и отметить эфир как активный (OBS подключился)."""
    stream = await Stream.get_by_rtmp_key(db, rtmp_key)
    if not stream:
        return None
    if stream.end_time is not None:
        return None
    if stream.archived_video_id:
        return None
    st = getattr(stream, "archive_status", None)
    if st in ("uploading", "completed"):
        return None

    _rtmp_offline_streak.pop(str(stream.id), None)
    return await promote_stream_live_on_rtmp(db, stream)


async def finalize_stream_on_rtmp_disconnect(
    db: AsyncSession,
    rtmp_key: str,
    background_tasks: BackgroundTasks,
) -> None:
    """OBS отключился — завершить эфир и запустить сохранение записи."""
    stream = await Stream.get_by_rtmp_key(db, rtmp_key)
    if not stream:
        return
    if not stream.start_time and not stream.is_live:
        return
    await finalize_stream_session(db, stream, background_tasks)
