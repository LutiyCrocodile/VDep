"""Pydantic models for streaming API."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class StreamCreate(BaseModel):
    title: str
    description: str = ""
    visibility: str = Field("dgi_employees", pattern="^(dgi_employees|private)$")
    allowed_user_ids: List[str] = []
    save_recording: bool = True


class StreamResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    rtmp_key: str
    hls_url: Optional[str]
    is_live: bool
    start_time: Optional[datetime]
    end_time: Optional[datetime] = None
    user_id: str
    visibility: str = "dgi_employees"
    save_recording: bool = True
    rtmp_server_url: str
    rtmp_stream_key: str
    owner_username: Optional[str] = None
    created_at: Optional[datetime] = None


class StreamDetailResponse(StreamResponse):
    likes_count: int = 0
    user_liked: bool = False
    viewers_count: int = 0
    channel_id: Optional[str] = None
    channel_handle: Optional[str] = None
    archived_video_id: Optional[str] = None

