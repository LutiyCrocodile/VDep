from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class VideoUploadResponse(BaseModel):
    video_id: str
    upload_url: str
    minio_key: str


class VideoResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    duration: Optional[int]
    resolution: Optional[str]
    bitrate: Optional[int]
    file_size: int
    status: str
    hls_playlist_url: Optional[str]
    thumbnail_url: Optional[str]
    is_private: bool
    tags: List[str]
    created_at: datetime
    user_id: str
    channel_id: Optional[str] = None
    views_count: int = 0
    owner_username: Optional[str] = None
    channel_handle: Optional[str] = None
    transcoding_progress: int = 0
    classification: str = "public"
    classification_id: Optional[str] = None
    classification_name: Optional[str] = None


class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    handle: str
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None


class ChannelResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    handle: str
    avatar_url: Optional[str]
    banner_url: Optional[str]
    owner_id: str
    subscribers_count: int
    is_verified: bool
    created_at: datetime


class SubscriptionResponse(BaseModel):
    id: str
    subscriber_id: str
    channel_id: str
    created_at: datetime


class ClassificationResponse(BaseModel):
    id: str
    name: str
    level: int
    description: Optional[str]
    created_at: datetime


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    classification_id: Optional[str] = None


class ViewRecordRequest(BaseModel):
    session_id: Optional[str] = None
    watched_duration: Optional[int] = None
