"""Generate streaming-service modules from main.py."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
lines = (ROOT / "main.py").read_text(encoding="utf-8").splitlines(keepends=True)


def sl(start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def rename_privates(body: str, mapping: dict[str, str]) -> str:
    for old, new in mapping.items():
        body = body.replace(old, new)
    return body


HTTP_CLIENT = '''"""Shared httpx client for service-to-service calls."""
from __future__ import annotations

from typing import Optional

import httpx

_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
'''

SCHEMAS_HEADER = '''"""Pydantic models for streaming API."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

'''

CONSTANTS = sl(303, 308) + "\n" + sl(378, 378) + """

from typing import Dict, Set

_archive_tasks_inflight: Set[str] = set()
_rtmp_offline_streak: Dict[str, int] = {}
RTMP_OFFLINE_FINALIZE_AFTER = 3
"""

DEPS_HEADER = '''"""FastAPI dependencies (auth, RBAC)."""
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

deps_body = sl(93, 168)
deps_body = deps_body.replace("_ensure_channel_exists", "ensure_channel_exists")
deps_body = deps_body.replace("httpx.AsyncClient() as client", "get_http_client() as client")

ACCESS_HEADER = '''"""Stream visibility and access control."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Stream, is_stream_viewer

'''

access_body = (
    sl(311, 317)
    + sl(320, 329)
    + sl(332, 353)
    + sl(286, 294).replace("_require_stream_view_access", "async def require_stream_view_access")
)
access_body = access_body.replace("_can_view_stream(", "def can_view_stream(")
access_body = access_body.replace("async def _can_view_stream_db", "async def can_view_stream_db")
access_body = access_body.replace("await _can_view_stream_db", "await can_view_stream_db")

STREAM_HELPERS_HEADER = '''"""Stream response builders and auth lookups."""
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

'''

helpers_body = sl(206, 283) + sl(297, 300) + sl(355, 375)
helpers_body = helpers_body.replace("_mediamtx_path", "mediamtx_path")
helpers_body = helpers_body.replace("_build_public_hls", "build_public_hls")
helpers_body = helpers_body.replace("_build_rtmp_server_url", "build_rtmp_server_url")
helpers_body = helpers_body.replace("_stream_saves_recording", "stream_saves_recording")
helpers_body = helpers_body.replace("_stream_likes_state", "stream_likes_state")
helpers_body = helpers_body.replace("_build_stream_detail", "async def build_stream_detail")
helpers_body = helpers_body.replace("_resolve_owner_usernames", "resolve_owner_usernames")
helpers_body = helpers_body.replace("_rtmp_key_from_mediamtx_path", "def rtmp_key_from_mediamtx_path")
helpers_body = helpers_body.replace("async def async def", "async def")
helpers_body = helpers_body.replace("httpx.AsyncClient(timeout=10.0) as client", "get_http_client() as client")

ARCHIVE_HEADER = '''"""Post-stream recording archive pipeline."""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .constants import (
    ARCHIVE_BLOCKING_PHASES,
    RECORDING_SUFFIXES,
    _archive_tasks_inflight,
)
from .database import (
    Stream,
    async_session,
    list_stream_viewer_ids,
    transfer_stream_likes_to_video,
)
from .stream_helpers import mediamtx_path, stream_saves_recording

logger = logging.getLogger(__name__)

'''

archive_body = sl(381, 667) + sl(888, 1007) + sl(1046, 1063)
archive_body = archive_body.replace("_mediamtx_path", "mediamtx_path")
archive_body = archive_body.replace("_stream_saves_recording", "stream_saves_recording")
archive_body = archive_body.replace("_collect_media_files", "collect_media_files")
archive_body = archive_body.replace("_discover_recording_paths", "discover_recording_paths")
archive_body = archive_body.replace("_wait_for_stable_recordings", "wait_for_stable_recordings")
archive_body = archive_body.replace("_build_mp4_from_paths", "build_mp4_from_paths")
archive_body = archive_body.replace("_set_archive_state", "set_archive_state")
archive_body = archive_body.replace("_seconds_since", "seconds_since")
archive_body = archive_body.replace("_fetch_video_status", "fetch_video_status")
archive_body = archive_body.replace("_archive_status_idle", "archive_status_idle")
archive_body = archive_body.replace("_resolve_stale_archive", "resolve_stale_archive")
archive_body = archive_body.replace("_enqueue_archive_task", "enqueue_archive_task")
archive_body = archive_body.replace("_schedule_archive_if_needed", "schedule_archive_if_needed")
archive_body = archive_body.replace("_archive_stream_task_impl", "archive_stream_task_impl")
archive_body = archive_body.replace("async def _go_live_archive_item", "async def go_live_archive_item")

RTMP_HEADER = '''"""RTMP / MediaMTX lifecycle and reconcile loop."""
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

'''

rtmp_body = sl(55, 65) + sl(670, 832)
rtmp_body = rtmp_body.replace("_rtmp_reconcile_loop", "async def rtmp_reconcile_loop")
rtmp_body = rtmp_body.replace("_mediamtx_path_has_publisher", "mediamtx_path_has_publisher")
rtmp_body = rtmp_body.replace("_finalize_stream_session", "finalize_stream_session")
rtmp_body = rtmp_body.replace("_promote_stream_live_on_rtmp", "promote_stream_live_on_rtmp")
rtmp_body = rtmp_body.replace("_reconcile_stream_rtmp_state", "reconcile_stream_rtmp_state")
rtmp_body = rtmp_body.replace("_notify_stream_live", "notify_stream_live")
rtmp_body = rtmp_body.replace("_mark_stream_live_on_rtmp_publish", "mark_stream_live_on_rtmp_publish")
rtmp_body = rtmp_body.replace("_finalize_stream_on_rtmp_disconnect", "finalize_stream_on_rtmp_disconnect")
rtmp_body = rtmp_body.replace("_schedule_archive_if_needed", "schedule_archive_if_needed")
rtmp_body = rtmp_body.replace("_mediamtx_path", "mediamtx_path")
rtmp_body = rtmp_body.replace("await _reconcile_stream_rtmp_state", "await reconcile_stream_rtmp_state")
rtmp_body = rtmp_body.replace("httpx.AsyncClient(timeout=3.0) as client", "get_http_client() as client")
rtmp_body = rtmp_body.replace("httpx.AsyncClient(timeout=10.0) as client", "get_http_client() as client")
rtmp_body = rtmp_body.replace("httpx.AsyncClient(timeout=20.0) as client", "get_http_client() as client")

INTERNAL_ROUTER = '''"""MediaMTX internal routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..rtmp import finalize_stream_on_rtmp_disconnect, mark_stream_live_on_rtmp_publish
from ..stream_helpers import rtmp_key_from_mediamtx_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/mediamtx")

''' + sl(835, 885).replace("@app.", "@router.").replace(
    "/internal/mediamtx/auth", "/auth"
).replace(
    "/internal/mediamtx/ready", "/ready"
).replace(
    "/internal/mediamtx/not-ready", "/not-ready"
)

STREAMS_ROUTER_HEADER = '''"""Public stream API routes."""
from __future__ import annotations

import asyncio
import logging
import uuid as uuid_lib
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
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
from ..stream_helpers import (
    build_stream_detail,
    build_public_hls,
    mediamtx_path,
    resolve_owner_usernames,
    stream_likes_state,
    to_stream_response,
)

logger = logging.getLogger(__name__)

router = APIRouter()

'''

streams_body = sl(1010, 1357).replace("@app.", "@router.")
streams_body = streams_body.replace("_can_view_stream_db", "can_view_stream_db")
streams_body = streams_body.replace("_build_stream_detail", "build_stream_detail")
streams_body = streams_body.replace("_require_stream_view_access", "require_stream_view_access")
streams_body = streams_body.replace("_resolve_owner_usernames", "resolve_owner_usernames")
streams_body = streams_body.replace("_go_live_archive_item", "go_live_archive_item")
streams_body = streams_body.replace("_reconcile_stream_rtmp_state", "reconcile_stream_rtmp_state")
streams_body = streams_body.replace("_ensure_channel_exists", "ensure_channel_exists")
streams_body = streams_body.replace("_mediamtx_path", "mediamtx_path")
streams_body = streams_body.replace("_build_public_hls", "build_public_hls")
streams_body = streams_body.replace("_stream_likes_state", "stream_likes_state")
streams_body = streams_body.replace("_schedule_archive_if_needed", "schedule_archive_if_needed")
streams_body = streams_body.replace("await build_archive_payload", "await build_archive_payload")

HEALTH_ROUTER = '''"""Health check."""
from fastapi import APIRouter

router = APIRouter()

''' + sl(1360, 1362).replace("@app.", "@router.")

NEW_MAIN = '''"""Streaming service — FastAPI entrypoint."""
from contextlib import asynccontextmanager
import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import async_session, create_tables, Stream
from .http_client import close_http_client
from .rtmp import reconcile_stream_rtmp_state, rtmp_reconcile_loop
from .routers import health, internal, streams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    reconcile_task = asyncio.create_task(rtmp_reconcile_loop())
    logger.info("Streaming service started")
    yield
    reconcile_task.cancel()
    try:
        await reconcile_task
    except asyncio.CancelledError:
        pass
    await close_http_client()
    logger.info("Streaming service shutting down")


app = FastAPI(title="Streaming Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(internal.router)
app.include_router(streams.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
'''

ROUTERS_INIT = '''"""HTTP routers."""
from . import health, internal, streams

__all__ = ["health", "internal", "streams"]
'''

files = {
    "http_client.py": HTTP_CLIENT,
    "schemas.py": SCHEMAS_HEADER + sl(171, 204),
    "constants.py": '"""Archive/RTMP constants."""\nfrom __future__ import annotations\n\n' + CONSTANTS,
    "deps.py": DEPS_HEADER + deps_body,
    "access.py": ACCESS_HEADER + access_body,
    "stream_helpers.py": STREAM_HELPERS_HEADER + helpers_body,
    "archive.py": ARCHIVE_HEADER + archive_body,
    "rtmp.py": RTMP_HEADER + rtmp_body,
    "routers/__init__.py": ROUTERS_INIT,
    "routers/internal.py": INTERNAL_ROUTER,
    "routers/streams.py": STREAMS_ROUTER_HEADER + streams_body,
    "routers/health.py": HEALTH_ROUTER,
    "main.py": NEW_MAIN,
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print("wrote", rel)

# backup legacy
legacy = ROOT / "main_legacy.py"
if not legacy.exists():
    legacy.write_text("".join(lines), encoding="utf-8")
    print("backed up main_legacy.py")

print("done")
