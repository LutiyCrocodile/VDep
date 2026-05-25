"""internal routes."""
from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile
from minio.error import S3Error
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..access import (
    can_access_classification,
    enforce_video_view_access,
    get_user_classification_level,
    user_can_view_video,
)
from ..config import settings
from ..database import Channel, Subscription, Video, VideoUserAccess, get_db
from ..deps import (
    generate_minio_key,
    minio_client,
    parse_duration,
    require_current_user,
    require_internal_token,
    start_transcoding,
)
from ..schemas import (
    ChannelCreate,
    ChannelResponse,
    SubscriptionResponse,
    VideoResponse,
    VideoUpdate,
    VideoUploadResponse,
    ViewRecordRequest,
)
from ..storage import get_playlist_url, get_thumbnail_url, stream_media_object

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/internal/channels/by-owner/{owner_id}", response_model=ChannelResponse)
async def internal_get_channel_by_owner(
    owner_id: str,
    _ok: bool = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """Service-to-service: resolve channel by owner user id (UUID)."""
    channel = await Channel.get_by_owner(db, owner_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        description=channel.description,
        handle=channel.handle,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        owner_id=str(channel.owner_id),
        subscribers_count=channel.subscribers_count or 0,
        is_verified=channel.is_verified or False,
        created_at=channel.created_at,
    )


@router.get("/internal/channels/{channel_id}/subscriber-ids")
async def internal_channel_subscriber_ids(
    channel_id: str,
    _ok: bool = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """Список user_id подписчиков канала (для notification-service)."""
    channel = await Channel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    ids = await Subscription.get_channel_subscriber_ids(db, channel_id)
    return {"channel_id": channel_id, "subscriber_ids": ids}


@router.get("/internal/videos/{video_id}/status")
async def internal_video_processing_status(
    video_id: str,
    _ok: bool = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """Статус обработки видео для streaming-service (прогресс трансляции)."""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return {
        "id": str(video.id),
        "status": video.status,
        "transcoding_progress": video.transcoding_progress or 0,
        "hls_playlist_url": video.hls_playlist_url,
        "title": video.title,
    }


@router.post("/internal/videos/from-recording")
async def internal_create_video_from_recording(
    background_tasks: BackgroundTasks,
    _ok: bool = Depends(require_internal_token),
    user_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    classification: str = Form("internal"),
    is_private: str = Form("false"),
    invited_user_ids: str = Form(""),  # comma-separated UUIDs for restricted archive
    source_stream_id: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a finished live recording to MinIO, create a video row on the owner's channel,
    start transcoding. For private streams use classification=restricted and invited_user_ids.
    """
    is_private_bool = str(is_private).lower() in ("true", "1", "yes")
    channel = await Channel.get_by_owner(db, user_id)
    if not channel:
        raise HTTPException(status_code=400, detail="Owner has no channel")

    video_id = str(uuid.uuid4())
    minio_key = generate_minio_key(video_id, file.filename or "live-recording.mp4")

    chunk_size = 1024 * 1024
    chunks: List[bytes] = []
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
    file_data = b"".join(chunks)
    file_size = len(file_data)
    if file_size < 1:
        raise HTTPException(status_code=400, detail="Empty recording file")

    try:
        minio_client.put_object(
            settings.minio_bucket,
            minio_key,
            io.BytesIO(file_data),
            file_size,
            content_type=file.content_type or "video/mp4",
        )
    except S3Error as e:
        logger.error(f"MinIO upload (recording) error: {e}")
        raise HTTPException(status_code=500, detail="Failed to store recording")

    tags_list = ["live", "recording"]
    await Video.create(
        db,
        **{
            "id": video_id,
            "title": title,
            "description": description,
            "user_id": user_id,
            "channel_id": str(channel.id),
            "file_size": file_size,
            "minio_key": minio_key,
            "status": "uploaded",
            "is_private": is_private_bool,
            "tags": tags_list,
            "classification": classification,
        },
    )

    if classification == "restricted" and invited_user_ids.strip():
        for raw in invited_user_ids.split(","):
            uid = raw.strip()
            if uid and not await VideoUserAccess.grant_access(db, video_id, uid, user_id):
                logger.warning("Could not grant stream archive access to user %s for video %s", uid, video_id)

    sid = source_stream_id.strip()
    if sid:
        src_key = f"streams/{sid}/thumbnail.jpg"
        dst_key = f"{video_id}/thumbnail.jpg"
        thumb_db_path = f"/{video_id}/thumbnail.jpg"
        try:
            from minio.commonconfig import CopySource

            minio_client.copy_object(
                settings.minio_bucket,
                dst_key,
                CopySource(settings.minio_bucket, src_key),
            )
            await Video.update_metadata(db, video_id, thumbnail_url=thumb_db_path)
            logger.info("Copied stream %s thumbnail to video %s", sid, video_id)
        except S3Error as e:
            logger.warning("No stream thumbnail to copy for %s: %s", sid, e)

    background_tasks.add_task(start_transcoding, video_id, minio_key)
    return {"video_id": video_id, "minio_key": minio_key, "status": "transcoding_started"}
