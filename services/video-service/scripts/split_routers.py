"""Split main.py route handlers into routers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
lines = (ROOT / "main.py").read_text(encoding="utf-8").splitlines(keepends=True)


def make_header(module: str) -> str:
    return f'''"""{module} routes."""
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

'''


def extract_ranges(ranges: list[tuple[int, int]], skip: list[tuple[int, int]] | None = None) -> str:
    skip = skip or []
    out = []
    for start, end in ranges:
        for i in range(start - 1, end):
            line_no = i + 1
            if any(a <= line_no <= b for a, b in skip):
                continue
            line = lines[i]
            if line.startswith("@app."):
                line = line.replace("@app.", "@router.", 1)
            out.append(line)
    return "".join(out)


def write_router(name: str, ranges: list[tuple[int, int]], skip=None):
    (ROOT / "routers").mkdir(exist_ok=True)
    body = extract_ranges(ranges, skip)
    path = ROOT / "routers" / f"{name}.py"
    path.write_text(make_header(name) + body, encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    write_router("internal", [(208, 341)])
    write_router("media", [(576, 608)])
    write_router("videos", [(348, 509), (618, 1230)], skip=[(1231, 1260)])
    write_router("channels", [(1261, 1576)])
    write_router("health", [(1577, 1579)])
    print("done")
