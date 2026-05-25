"""Public stream API routes."""
from __future__ import annotations

import asyncio
import io
import logging
import uuid as uuid_lib
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from minio.error import S3Error
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..access import require_stream_view_access
from ..access import can_view_stream_db
from ..archive import (
    archive_stream_task,
    build_archive_payload,
    go_live_archive_item,
    schedule_archive_if_needed,
)
from ..database import (
    Stream,
    add_stream_like,
    get_db,
    remove_stream_like,
    replace_stream_viewers,
    user_liked_stream,
    user_liked_video,
)
from ..deps import (
    ensure_channel_exists,
    get_current_user_id,
    get_current_user_with_permissions,
    get_optional_profile,
    require_permission,
)
from ..presence import count_viewers, leave_presence, touch_presence
from ..rtmp import reconcile_stream_rtmp_state
from ..schemas import StreamCreate, StreamDetailResponse, StreamResponse
from ..config import settings
from ..minio_client import minio_client
from ..storage_urls import (
    get_public_thumbnail_url,
    stream_thumbnail_db_path,
    stream_thumbnail_minio_key,
)
from ..stream_helpers import (
    build_stream_detail,
    build_public_hls,
    mediamtx_path as build_mediamtx_path,
    resolve_owner_usernames,
    stream_likes_state,
    stream_saves_recording,
    stream_thumbnail_cache_version,
    to_stream_response,
)
from ..thumbnail_processing import (
    ALLOWED_CONTENT_TYPES,
    MAX_THUMBNAIL_BYTES,
    process_custom_thumbnail,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _assert_owner_can_edit_stream_thumbnail(stream: Stream, user_id: str) -> None:
    if str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    # Разрешено до завершения эфира и пока запись ещё не привязана к видео на канале
    if stream.archived_video_id:
        raise HTTPException(
            status_code=400,
            detail="Превью нельзя изменить после сохранения записи на канал",
        )


def _remove_stream_thumbnail_object(stream_id: str) -> None:
    try:
        minio_client.remove_object(settings.minio_bucket, stream_thumbnail_minio_key(stream_id))
    except S3Error:
        pass


@router.get("/streams/live")
async def get_live_streams_public_filtered(
    db: AsyncSession = Depends(get_db),
    profile: Optional[dict] = Depends(get_optional_profile),
):
    """Список активных эфиров с учётом видимости (сотрудники ДГИ / приватные приглашённые)."""
    rows = await Stream.get_live_streams(db)
    visible: List[Stream] = []
    for s in rows:
        if await can_view_stream_db(db, s, profile):
            visible.append(s)
    owner_names = await resolve_owner_usernames({str(s.user_id) for s in visible})
    items: List[dict] = []
    for s in visible:
        r = to_stream_response(s)
        uid = str(s.user_id)
        sid = str(s.id)
        likes_count, _ = await stream_likes_state(db, s, None)
        items.append(
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "hls_url": r.hls_url,
                "is_live": r.is_live,
                "user_id": r.user_id,
                "owner_username": owner_names.get(uid),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "viewers_count": count_viewers(sid),
                "likes_count": likes_count,
                "visibility": r.visibility,
                "thumbnail_url": get_public_thumbnail_url(
                    getattr(s, "thumbnail_url", None), sid, allow_default=True
                ),
                "thumbnail_cache_version": stream_thumbnail_cache_version(s),
            }
        )
    return {"streams": items}


@router.post("/streams", response_model=StreamResponse)
async def create_stream(
    stream_data: StreamCreate,
    user_id: str = Depends(require_permission("video:stream")),
    db: AsyncSession = Depends(get_db),
):
    await ensure_channel_exists(user_id)
    open_session = await Stream.get_open_session_for_owner(db, user_id)
    if open_session:
        raise HTTPException(
            status_code=409,
            detail="Сначала завершите или отмените текущую подготовку трансляции",
        )

    rtmp_key = str(uuid_lib.uuid4()).replace("-", "")[:16]
    mtx_path = build_mediamtx_path(rtmp_key)
    hls_url = build_public_hls(mtx_path)

    stream = await Stream.create(
        db,
        **{
            "title": stream_data.title,
            "description": stream_data.description,
            "user_id": user_id,
            "rtmp_key": rtmp_key,
            "hls_url": hls_url,
            "visibility": stream_data.visibility,
            "mediamtx_path": mtx_path,
            "save_recording": stream_data.save_recording,
        },
    )
    if stream_data.visibility == "private" and stream_data.allowed_user_ids:
        await replace_stream_viewers(db, str(stream.id), stream_data.allowed_user_ids)

    return to_stream_response(stream)


@router.get("/streams/my-active")
async def get_my_active_stream(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    go-live: активная подготовка/эфир + список фоновых архиваций (не блокируют новый эфир).
    """
    active = await Stream.get_open_session_for_owner(db, user_id)
    if active:
        active = await reconcile_stream_rtmp_state(db, active)
        if active.end_time is not None:
            active = None
    active_payload = None
    rtmp_state = None
    if active:
        active_payload = to_stream_response(active).model_dump(mode="json")
        rtmp_state = "live" if active.is_live else "waiting_obs"

    archiving_items: List[Dict[str, Any]] = []
    active_id = str(active.id) if active else None
    for ended in await Stream.get_recent_ended_for_owner(db, user_id, limit=8):
        if active_id and str(ended.id) == active_id:
            continue
        item = await go_live_archive_item(ended, db)
        if item:
            archiving_items.append(item)

    return {
        "stream": active_payload,
        "rtmp_state": rtmp_state,
        "archiving": archiving_items,
    }


@router.get("/streams/{stream_id}/archive-status")
async def get_stream_archive_status(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    archive = await build_archive_payload(stream, db)
    return {"stream_id": stream_id, **archive}


@router.post("/streams/{stream_id}/archive/dismiss")
async def dismiss_stream_archive(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Сбросить зависшую обработку записи (после удаления видео или ошибки)."""
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    await Stream.dismiss_archive_ui(db, stream_id)
    return {"message": "Блок архивации скрыт", "archive": {"phase": "idle", "progress": 0, "video_id": None}}


@router.post("/streams/{stream_id}/archive/retry")
async def retry_stream_archive(
    stream_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Повторить сохранение записи только если видео ещё не создано."""
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    if not stream.end_time:
        raise HTTPException(status_code=400, detail="Сначала остановите трансляцию")
    if not stream_saves_recording(stream):
        raise HTTPException(status_code=400, detail="Для этого эфира сохранение записи отключено")
    if stream.archived_video_id:
        vs = await _fetch_video_status(str(stream.archived_video_id))
        if vs and not vs.get("missing"):
            raise HTTPException(
                status_code=400,
                detail="Запись уже загружена на канал. Дождитесь обработки или откройте канал.",
            )
    if stream_id in _archive_tasks_inflight:
        return {"message": "Сохранение записи уже выполняется"}
    await Stream.reset_archive(db, stream_id)
    await Stream.update_status(db, stream_id, archive_status="pending", archive_error=None)
    await schedule_archive_if_needed(stream_id, background_tasks)
    return {"message": "Повторное сохранение запущено в фоне"}


@router.get("/streams", response_model=List[StreamResponse])
async def list_streams(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    streams = await Stream.get_all(db, user_id=user_id)
    return [to_stream_response(s) for s in streams]


@router.get("/streams/{stream_id}", response_model=StreamDetailResponse)
async def get_stream(
    stream_id: str,
    profile: Optional[dict] = Depends(get_optional_profile),
    db: AsyncSession = Depends(get_db),
):
    stream = await require_stream_view_access(db, stream_id, profile)
    if stream.end_time is None:
        stream = await reconcile_stream_rtmp_state(db, stream)
        stream = await Stream.get_by_id(db, stream_id) or stream
    return await build_stream_detail(db, stream, profile)


@router.post("/streams/{stream_id}/thumbnail")
async def upload_stream_thumbnail(
    stream_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Превью до/во время подготовки эфира (пока трансляция не завершена)."""
    stream = await Stream.get_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    _assert_owner_can_edit_stream_thumbnail(stream, user_id)

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Пустой файл")
    if len(raw) > MAX_THUMBNAIL_BYTES:
        raise HTTPException(status_code=413, detail="Максимальный размер превью: 5 МБ")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Допустимые форматы: JPEG, PNG, WebP")

    try:
        jpeg_bytes = process_custom_thumbnail(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    minio_key = stream_thumbnail_minio_key(stream_id)
    db_path = stream_thumbnail_db_path(stream_id)
    try:
        minio_client.put_object(
            settings.minio_bucket,
            minio_key,
            io.BytesIO(jpeg_bytes),
            len(jpeg_bytes),
            content_type="image/jpeg",
        )
        await Stream.update_thumbnail(db, stream_id, db_path)
    except S3Error as e:
        logger.error("Stream thumbnail upload error: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось сохранить превью") from e

    stream = await Stream.get_by_id(db, stream_id) or stream
    public_url = get_public_thumbnail_url(db_path, stream_id)
    cache_version = stream_thumbnail_cache_version(stream)
    return {
        "message": "Thumbnail uploaded",
        "thumbnail_url": public_url,
        "thumbnail_cache_version": cache_version,
    }


@router.delete("/streams/{stream_id}/thumbnail")
async def delete_stream_thumbnail(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    stream = await Stream.get_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    _assert_owner_can_edit_stream_thumbnail(stream, user_id)

    _remove_stream_thumbnail_object(stream_id)
    await Stream.update_thumbnail(db, stream_id, None)
    return {"message": "Thumbnail removed"}


@router.post("/streams/{stream_id}/presence")
async def stream_presence_heartbeat(
    stream_id: str,
    profile: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db),
):
    stream = await require_stream_view_access(db, stream_id, profile)
    touch_presence(str(stream.id), str(profile["id"]))
    return {"viewers_count": count_viewers(str(stream.id))}


@router.post("/streams/{stream_id}/presence/leave")
async def stream_presence_leave(
    stream_id: str,
    profile: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db),
):
    stream = await require_stream_view_access(db, stream_id, profile)
    leave_presence(str(stream.id), str(profile["id"]))
    return {"viewers_count": count_viewers(str(stream.id))}


@router.post("/streams/{stream_id}/like")
async def like_stream(
    stream_id: str,
    profile: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db),
):
    stream = await require_stream_view_access(db, stream_id, profile)
    user_id = str(profile["id"])
    if stream.archived_video_id:
        vid = str(stream.archived_video_id)
        if not await user_liked_video(db, vid, user_id):
            await db.execute(
                text(
                    """
                    INSERT INTO video_likes (id, video_id, user_id, created_at)
                    VALUES (gen_random_uuid(), CAST(:vid AS uuid), CAST(:uid AS uuid), NOW())
                    ON CONFLICT ON CONSTRAINT uq_video_likes_video_user DO NOTHING
                    """
                ),
                {"vid": vid, "uid": user_id},
            )
            await db.commit()
    else:
        await add_stream_like(db, stream_id, user_id)
    likes_count, user_liked = await stream_likes_state(db, stream, user_id)
    return {"likes_count": likes_count, "user_liked": user_liked}


@router.delete("/streams/{stream_id}/like")
async def unlike_stream(
    stream_id: str,
    profile: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db),
):
    stream = await require_stream_view_access(db, stream_id, profile)
    user_id = str(profile["id"])
    if stream.archived_video_id:
        vid = str(stream.archived_video_id)
        await db.execute(
            text(
                "DELETE FROM video_likes WHERE video_id = CAST(:vid AS uuid) AND user_id = CAST(:uid AS uuid)"
            ),
            {"vid": vid, "uid": user_id},
        )
        await db.commit()
    else:
        await remove_stream_like(db, stream_id, user_id)
    likes_count, user_liked = await stream_likes_state(db, stream, user_id)
    return {"likes_count": likes_count, "user_liked": user_liked}


@router.put("/streams/{stream_id}/start")
async def start_stream(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Устарело: эфир включается автоматически при публикации RTMP из OBS."""
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    if stream.end_time is not None:
        raise HTTPException(status_code=400, detail="Трансляция уже завершена")

    return {
        "message": "Эфир начнётся автоматически при нажатии «Начать трансляцию» в OBS",
        "stream_id": stream_id,
        "stream": to_stream_response(stream).model_dump(),
    }


@router.post("/streams/{stream_id}/cancel")
async def cancel_prepared_stream(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Отменить подготовку эфира (OBS ещё не подключался)."""
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    if stream.is_live:
        raise HTTPException(status_code=400, detail="Остановите трансляцию в OBS")
    if stream.start_time:
        raise HTTPException(status_code=400, detail="Эфир уже был в эфире — дождитесь архивации или остановите в OBS")
    if stream.end_time is not None:
        raise HTTPException(status_code=400, detail="Трансляция уже завершена")

    _remove_stream_thumbnail_object(stream_id)
    await Stream.update_thumbnail(db, stream_id, None)
    await Stream.update_status(db, stream_id, is_live=False, end_time=datetime.utcnow())
    return {"message": "Подготовка отменена"}


@router.put("/streams/{stream_id}/stop")
async def stop_stream(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Завершение эфира только через OBS (MediaMTX runOnNotReady)."""
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")

    raise HTTPException(
        status_code=400,
        detail="Завершите трансляцию в OBS: остановите вывод или отключите RTMP. "
        "С сайта эфир завершить нельзя — иначе поток в OBS продолжит идти.",
    )


@router.websocket("/ws/streams/{stream_id}")
async def stream_websocket(websocket: WebSocket, stream_id: str):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping", "stream_id": stream_id})
    except WebSocketDisconnect:
        logger.info("WS disconnected %s", stream_id)
