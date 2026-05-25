"""channels routes."""
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

@router.post("/channels", response_model=ChannelResponse)
async def create_channel(
    channel_data: ChannelCreate,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"POST /channels - user_id from token: {user_id} (type: {type(user_id)})")
    
    # Check if user already has a channel
    existing_channel = await Channel.get_by_owner(db, user_id)
    logger.info(f"Existing channel check: {existing_channel}")
    if existing_channel:
        logger.warning(f"User {user_id} already has channel: {existing_channel.id}")
        raise HTTPException(status_code=400, detail="User already has a channel")
    
    # Check if handle is already taken
    existing_handle = await Channel.get_by_handle(db, channel_data.handle)
    if existing_handle:
        raise HTTPException(status_code=400, detail="Handle already taken")
    
    logger.info(f"Creating channel with owner_id: {user_id}")
    channel = await Channel.create(db, **{
        "name": channel_data.name,
        "description": channel_data.description,
        "handle": channel_data.handle,
        "avatar_url": channel_data.avatar_url,
        "banner_url": channel_data.banner_url,
        "owner_id": user_id
    })
    logger.info(f"Channel created: id={channel.id}, owner_id={channel.owner_id}")
    
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        description=channel.description,
        handle=channel.handle,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        owner_id=str(channel.owner_id),
        subscribers_count=channel.subscribers_count,
        is_verified=channel.is_verified,
        created_at=channel.created_at
    )

# NOTE: /channels/my must be BEFORE /channels/{channel_id} to avoid routing conflicts
@router.get("/channels/my", response_model=ChannelResponse)
async def get_my_channel(
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"GET /channels/my - user_id from token: {user_id} (type: {type(user_id)})")
    channel = await Channel.get_by_owner(db, user_id)
    logger.info(f"Channel lookup result: {channel}")
    if not channel:
        logger.warning(f"Channel not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        description=channel.description,
        handle=channel.handle,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        owner_id=str(channel.owner_id),
        subscribers_count=channel.subscribers_count,
        is_verified=channel.is_verified,
        created_at=channel.created_at
    )

@router.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    channel = await Channel.get_by_id(db, channel_id)
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
        subscribers_count=channel.subscribers_count,
        is_verified=channel.is_verified,
        created_at=channel.created_at
    )

@router.get("/channels/handle/{handle}", response_model=ChannelResponse)
async def get_channel_by_handle(
    handle: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get channel by handle (e.g., @username)"""
    channel = await Channel.get_by_handle(db, handle)
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
        subscribers_count=channel.subscribers_count,
        is_verified=channel.is_verified,
        created_at=channel.created_at
    )

@router.get("/channels/{channel_id}/videos", response_model=List[VideoResponse])
async def get_channel_videos(
    channel_id: str,
    skip: int = 0,
    limit: int = 50,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get channel info for owner_username
    channel = await Channel.get_by_id(db, channel_id)
    channel_name = channel.name if channel else "Неизвестный"
    is_owner = channel and str(channel.owner_id) == user_id

    videos = await Video.get_all(db, skip=skip, limit=limit, channel_id=channel_id)

    if is_owner:
        # Владелец видит загрузку / транскодинг с progress bar
        filtered_videos = list(videos)
    else:
        videos_ready = [v for v in videos if (v.status or "") == "ready"]
        allowed: List[Video] = []
        for v in videos_ready:
            if await user_can_view_video(db, v, user_id):
                allowed.append(v)
        filtered_videos = allowed
    
    return [
        VideoResponse(
            id=str(v.id),
            title=v.title,
            description=v.description,
            duration=parse_duration(v.duration),
            resolution=v.resolution,
            bitrate=v.bitrate,
            file_size=v.file_size,
            status=v.status,
            hls_playlist_url=get_playlist_url(v.hls_playlist_url or ""),
            thumbnail_url=get_thumbnail_url(v.thumbnail_url),
            is_private=v.is_private,
            tags=v.tags or [],
            created_at=v.created_at,
            user_id=str(v.user_id),
            channel_id=str(v.channel_id) if v.channel_id else None,
            views_count=v.views_count or 0,
            owner_username=channel_name,
            channel_handle=channel.handle if channel else None,
            transcoding_progress=v.transcoding_progress or 0,
            classification=v.classification or 'public'
        ) for v in filtered_videos
    ]

# Video access management endpoints for 'restricted' (personal) videos
@router.post("/videos/{video_id}/access")
async def grant_video_access(
    video_id: str,
    target_user_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Grant access to a specific user for a personal (restricted) video"""
    logger.info(f"[Grant Access] Granting access to video {video_id} for user {target_user_id} by {user_id}")

    # Verify video ownership
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        logger.error(f"[Grant Access] Video not found or not owned by user")
        raise HTTPException(status_code=404, detail="Video not found")

    # Only restricted videos can have specific user access
    if video.classification != 'restricted':
        logger.error(f"[Grant Access] Video classification is not restricted: {video.classification}")
        raise HTTPException(status_code=400, detail="User access can only be granted for 'restricted' (personal) videos")

    success = await VideoUserAccess.grant_access(db, video_id, target_user_id, user_id)
    logger.info(f"[Grant Access] Grant access result: {success}")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to grant access")

    return {"message": "Access granted successfully"}

@router.delete("/videos/{video_id}/access/{target_user_id}")
async def revoke_video_access(
    video_id: str,
    target_user_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke access from a user for a personal video"""
    # Verify video ownership
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")
    
    await VideoUserAccess.revoke_access(db, video_id, target_user_id)
    return {"message": "Access revoked successfully"}

@router.get("/videos/{video_id}/access")
async def get_video_access_list(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of users with access to a personal video"""
    # Verify video ownership
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")
    
    users = await VideoUserAccess.get_allowed_users(db, video_id)
    return {"users": users}

# Subscription endpoints
@router.post("/channels/{channel_id}/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_channel(
    channel_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if channel exists
    channel = await Channel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if already subscribed
    if await Subscription.is_subscribed(db, user_id, channel_id):
        raise HTTPException(status_code=400, detail="Already subscribed")
    
    # Cannot subscribe to own channel
    if str(channel.owner_id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot subscribe to own channel")
    
    subscription = await Subscription.create(db, **{
        "subscriber_id": user_id,
        "channel_id": channel_id
    })
    
    return SubscriptionResponse(
        id=str(subscription.id),
        subscriber_id=str(subscription.subscriber_id),
        channel_id=str(subscription.channel_id),
        created_at=subscription.created_at
    )

@router.delete("/channels/{channel_id}/subscribe")
async def unsubscribe_from_channel(
    channel_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if channel exists
    channel = await Channel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if subscribed
    if not await Subscription.is_subscribed(db, user_id, channel_id):
        raise HTTPException(status_code=400, detail="Not subscribed")
    
    await Subscription.delete(db, user_id, channel_id)
    
    return {"message": "Unsubscribed successfully"}

@router.get("/channels/{channel_id}/is_subscribed")
async def check_subscription(
    channel_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    is_subscribed = await Subscription.is_subscribed(db, user_id, channel_id)
    return {"is_subscribed": is_subscribed}

@router.get("/subscriptions", response_model=List[ChannelResponse])
async def get_user_subscriptions(
    skip: int = 0,
    limit: int = 10,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    channels = await Subscription.get_user_subscriptions(db, user_id, skip=skip, limit=limit)
    return [
        ChannelResponse(
            id=str(c.id),
            name=c.name,
            description=c.description,
            handle=c.handle,
            avatar_url=c.avatar_url,
            banner_url=c.banner_url,
            owner_id=str(c.owner_id),
            subscribers_count=c.subscribers_count,
            is_verified=c.is_verified,
            created_at=c.created_at
        ) for c in channels
    ]

