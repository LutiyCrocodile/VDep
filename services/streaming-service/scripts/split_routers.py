"""Split streaming-service main.py into routers and support modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
lines = (ROOT / "main.py").read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def router_header(name: str, extra_imports: str = "") -> str:
    return f'''"""{name} routes."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..access import can_view_stream_db, require_stream_view_access
from ..archive import (
    archive_stream_task,
    build_archive_payload,
    go_live_archive_item,
)
from ..config import settings
from ..database import (
    Stream,
    add_stream_like,
    get_db,
    get_stream_likes_count,
    get_video_likes_count,
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
from ..rtmp import finalize_stream_on_rtmp_disconnect, mark_stream_live_on_rtmp_publish, reconcile_stream_rtmp_state
from ..schemas import StreamCreate, StreamDetailResponse, StreamResponse
from ..stream_helpers import build_stream_detail, resolve_owner_usernames, rtmp_key_from_mediamtx_path, to_stream_response
{extra_imports}

logger = logging.getLogger(__name__)

router = APIRouter()

'''


def internal_header() -> str:
    return '''"""MediaMTX internal routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..rtmp import finalize_stream_on_rtmp_disconnect, mark_stream_live_on_rtmp_publish
from ..stream_helpers import rtmp_key_from_mediamtx_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/mediamtx")

'''


def patch_app_to_router(body: str) -> str:
    return body.replace("@app.", "@router.")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    write(ROOT / "http_client.py", slice_lines(1, 1) or "")  # placeholder
    # http_client is hand-written separately

    write(
        ROOT / "schemas.py",
        '''"""Pydantic models for streaming API."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

'''
        + slice_lines(171, 204),
    )

    write(
        ROOT / "constants.py",
        '''"""Shared constants and in-memory RTMP/archive state."""
from __future__ import annotations

from typing import Dict, Set

ARCHIVE_BLOCKING_PHASES = frozenset(
    {"pending", "waiting_recording", "uploading", "transcoding", "failed"}
)
ARCHIVE_IN_PROGRESS_PHASES = frozenset(
    {"pending", "waiting_recording", "uploading", "transcoding"}
)

RECORDING_SUFFIXES = (".mp4", ".m4v", ".webm", ".ts", ".m4s", ".part")

_archive_tasks_inflight: Set[str] = set()
_rtmp_offline_streak: Dict[str, int] = {}
RTMP_OFFLINE_FINALIZE_AFTER = 3
''',
    )

    deps_body = slice_lines(51, 52) + slice_lines(93, 168)
    deps_body = deps_body.replace("security = HTTPBearer()", "").replace(
        "security_optional = HTTPBearer(auto_error=False)", ""
    )
    write(
        ROOT / "deps.py",
        '''"""FastAPI dependencies (auth, RBAC)."""
from __future__ import annotations

from typing import Optional

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth_client import auth_client
from .config import settings
from .http_client import get_http_client

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

'''
        + deps_body.replace("async def _ensure_channel_exists", "async def ensure_channel_exists")
        .replace("_ensure_channel_exists", "ensure_channel_exists"),
    )

    access_body = (
        slice_lines(308, 315)
        + slice_lines(320, 326)
        + slice_lines(332, 353)
        + slice_lines(286, 294).replace("_require_stream_view_access", "async def require_stream_view_access")
    )
    write(
        ROOT / "access.py",
        '''"""Stream visibility and access control."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Stream, is_stream_viewer

'''
        + access_body.replace("_can_view_stream(", "def can_view_stream(")
        .replace("_can_view_stream_db", "async def can_view_stream_db")
        .replace("async def async def", "async def"),
    )

    print("Run manual step: archive.py, rtmp.py, stream_helpers.py, routers — see split_routers phase 2")
