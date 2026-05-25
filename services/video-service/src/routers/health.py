"""health routes."""
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

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
