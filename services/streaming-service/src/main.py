from contextlib import asynccontextmanager
import asyncio
import json
import logging
import os
import shutil
import subprocess
import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn

from .auth_client import auth_client
from .config import settings
from .database import (
    Stream,
    add_stream_like,
    async_session,
    create_tables,
    get_channel_for_owner,
    get_db,
    get_stream_likes_count,
    get_video_likes_count,
    is_stream_viewer,
    list_stream_viewer_ids,
    remove_stream_like,
    replace_stream_viewers,
    transfer_stream_likes_to_video,
    user_liked_stream,
    user_liked_video,
)
from .presence import count_viewers, leave_presence, touch_presence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_archive_tasks_inflight: Set[str] = set()

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def _rtmp_reconcile_loop() -> None:
    """Периодически завершает эфиры без RTMP-публикатора (webhook MediaMTX в образе не работает)."""
    await asyncio.sleep(5)
    while True:
        try:
            async with async_session() as db:
                for stream in await Stream.get_streams_for_rtmp_reconcile(db):
                    await _reconcile_stream_rtmp_state(db, stream)
        except Exception:
            logger.exception("RTMP reconcile loop error")
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    reconcile_task = asyncio.create_task(_rtmp_reconcile_loop())
    logger.info("Streaming service started")
    yield
    reconcile_task.cancel()
    try:
        await reconcile_task
    except asyncio.CancelledError:
        pass
    logger.info("Streaming service shutting down")


app = FastAPI(title="Streaming Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.auth_service_url}/users/me",
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()["id"]
            raise HTTPException(status_code=401, detail="Invalid token")
        except HTTPException:
            raise
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


async def get_optional_profile(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
) -> Optional[dict]:
    if not credentials:
        return None
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.auth_service_url}/users/me",
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            return None
        except httpx.RequestError:
            return None


async def get_current_user_with_permissions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token required")
    user_data = await auth_client.verify_token(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    permissions = await auth_client.get_user_service_permissions(user_data["id"])
    if not permissions:
        raise HTTPException(status_code=403, detail="Нет доступа к видеосервису (RBAC)")

    return {
        "id": user_data["id"],
        "username": user_data["username"],
        "permissions": permissions.get("permissions", []),
        "is_employee": user_data.get("is_employee", True),
    }


def require_permission(permission: str):
    async def dependency(user=Depends(get_current_user_with_permissions)):
        if permission not in user["permissions"]:
            raise HTTPException(status_code=403, detail=f"Нужно право: {permission}")
        return user["id"]

    return dependency


async def _ensure_channel_exists(owner_id: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.video_service_url}/internal/channels/by-owner/{owner_id}",
            headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
            timeout=15.0,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=403,
                detail="Сначала создайте канал для запуска трансляции",
            )


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


def _mediamtx_path(rtmp_key: str) -> str:
    return f"{settings.rtmp_app}/{rtmp_key}"


def _build_public_hls(mediamtx_path: str) -> str:
    return f"{settings.public_hls_base.rstrip('/')}/{mediamtx_path}/index.m3u8"


def _build_rtmp_server_url() -> str:
    return f"rtmp://{settings.public_rtmp_host}:{settings.public_rtmp_port}/{settings.rtmp_app}"


def to_stream_response(s: Stream) -> StreamResponse:
    path = getattr(s, "mediamtx_path", None) or _mediamtx_path(s.rtmp_key)
    hls = _build_public_hls(path)
    vis = getattr(s, "visibility", None) or ("private" if s.is_private else "dgi_employees")
    return StreamResponse(
        id=str(s.id),
        title=s.title,
        description=s.description,
        rtmp_key=s.rtmp_key,
        hls_url=hls,
        is_live=bool(s.is_live),
        start_time=s.start_time,
        end_time=s.end_time,
        user_id=str(s.user_id),
        visibility=vis,
        save_recording=_stream_saves_recording(s),
        rtmp_server_url=_build_rtmp_server_url(),
        rtmp_stream_key=s.rtmp_key,
    )


def _stream_saves_recording(stream: Stream) -> bool:
    val = getattr(stream, "save_recording", None)
    if val is None:
        return True
    return bool(val)


async def _stream_likes_state(
    db: AsyncSession, stream: Stream, viewer_id: Optional[str]
) -> tuple[int, bool]:
    if stream.archived_video_id:
        vid = str(stream.archived_video_id)
        count = await get_video_likes_count(db, vid)
        liked = await user_liked_video(db, vid, viewer_id) if viewer_id else False
        return count, liked
    sid = str(stream.id)
    count = await get_stream_likes_count(db, sid)
    liked = await user_liked_stream(db, sid, viewer_id) if viewer_id else False
    return count, liked


async def _build_stream_detail(
    db: AsyncSession,
    stream: Stream,
    profile: Optional[dict],
) -> StreamDetailResponse:
    viewer_id = str(profile["id"]) if profile else None
    likes_count, user_liked = await _stream_likes_state(db, stream, viewer_id)
    names = await _resolve_owner_usernames({str(stream.user_id)})
    base = to_stream_response(stream)
    channel_id, channel_handle = await get_channel_for_owner(db, str(stream.user_id))
    detail = base.model_dump()
    detail.update(
        {
            "owner_username": names.get(str(stream.user_id)),
            "created_at": stream.created_at,
            "likes_count": likes_count,
            "user_liked": user_liked,
            "viewers_count": count_viewers(str(stream.id)),
            "channel_id": channel_id,
            "channel_handle": channel_handle,
            "archived_video_id": str(stream.archived_video_id) if stream.archived_video_id else None,
        }
    )
    return StreamDetailResponse(**detail)


async def _require_stream_view_access(
    db: AsyncSession, stream_id: str, profile: Optional[dict]
) -> Stream:
    stream = await Stream.get_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    if not await _can_view_stream_db(db, stream, profile):
        raise HTTPException(status_code=403, detail="Нет доступа к трансляции")
    return stream


def _rtmp_key_from_mediamtx_path(path: str) -> str:
    path = (path or "").strip("/")
    parts = path.split("/")
    return parts[-1] if parts else ""


ARCHIVE_BLOCKING_PHASES = frozenset(
    {"pending", "waiting_recording", "uploading", "transcoding", "failed"}
)
ARCHIVE_IN_PROGRESS_PHASES = frozenset(
    {"pending", "waiting_recording", "uploading", "transcoding"}
)


def _rtmp_session_active(stream: Stream) -> bool:
    """Ожидание OBS или эфир в процессе."""
    if bool(stream.is_live):
        return True
    if stream.end_time is None:
        return True
    return False


def _rtmp_ui_state(stream: Stream, archive_phase: str) -> str:
    if archive_phase in ("pending", "waiting_recording", "uploading", "transcoding", "failed"):
        return "archiving"
    if archive_phase == "ready":
        return "archive_ready"
    if stream.is_live:
        return "live"
    if stream.end_time is None:
        return "waiting_obs"
    return "idle"


def _can_view_stream(stream: Stream, profile: Optional[dict]) -> bool:
    if not profile:
        return False
    uid = str(profile["id"])
    if str(stream.user_id) == uid:
        return True
    vis = getattr(stream, "visibility", None) or ("private" if stream.is_private else "dgi_employees")
    if vis == "dgi_employees":
        return bool(profile.get("is_employee", True))
    return False


async def _can_view_stream_db(db: AsyncSession, stream: Stream, profile: Optional[dict]) -> bool:
    if _can_view_stream(stream, profile):
        return True
    if not profile:
        return False
    vis = getattr(stream, "visibility", None) or ("private" if stream.is_private else "dgi_employees")
    if vis == "private":
        return await is_stream_viewer(db, str(stream.id), str(profile["id"]))
    return False


async def _resolve_owner_usernames(user_ids: Set[str]) -> dict:
    """Логины владельцев эфиров по user_id (внутренний вызов auth-service)."""
    if not user_ids:
        return {}
    headers = {"Authorization": f"Bearer {settings.internal_auth_token}"}
    out: dict = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for uid in user_ids:
            uid_s = str(uid)
            try:
                r = await client.get(
                    f"{settings.auth_service_url}/internal/users/{uid_s}/profile-mini",
                    headers=headers,
                )
                if r.status_code == 200:
                    out[uid_s] = r.json().get("username") or "user"
                else:
                    out[uid_s] = "…"
            except httpx.RequestError:
                out[uid_s] = "…"
    return out


RECORDING_SUFFIXES = (".mp4", ".m4v", ".webm", ".ts", ".m4s", ".part")


def _collect_media_files(directory: str) -> List[str]:
    found: List[str] = []
    if not directory or not os.path.isdir(directory):
        return found
    for root, _, files in os.walk(directory):
        for name in files:
            lower = name.lower()
            if any(lower.endswith(s) for s in RECORDING_SUFFIXES):
                found.append(os.path.join(root, name))
    return found


def _discover_recording_paths(base_dir: str, mediamtx_path: str, rtmp_key: str) -> List[str]:
    candidates: List[str] = []
    if mediamtx_path:
        preferred = os.path.join(base_dir, *mediamtx_path.split("/"))
        candidates.extend(_collect_media_files(preferred))
    if not candidates and rtmp_key:
        narrowed: List[str] = []
        if os.path.isdir(base_dir):
            for root, _, files in os.walk(base_dir):
                for name in files:
                    lower = name.lower()
                    if not any(lower.endswith(s) for s in RECORDING_SUFFIXES):
                        continue
                    full = os.path.join(root, name)
                    if rtmp_key in full.replace(os.sep, "/"):
                        narrowed.append(full)
        candidates = narrowed
    return sorted(candidates, key=os.path.getmtime)


async def _wait_for_stable_recordings(
    base_dir: str, mediamtx_path: str, rtmp_key: str, attempts: int = 45, pause_sec: float = 2.0
) -> List[str]:
    """Ждём появления файла записи MediaMTX и стабильного размера (конец эфира)."""
    last_sizes: Dict[str, int] = {}
    for _ in range(attempts):
        paths = _discover_recording_paths(base_dir, mediamtx_path, rtmp_key)
        if paths:
            latest = paths[-1]
            try:
                size = os.path.getsize(latest)
            except OSError:
                size = 0
            prev = last_sizes.get(latest)
            last_sizes[latest] = size
            if size >= 2048 and prev is not None and size == prev:
                return paths
        await asyncio.sleep(pause_sec)
    return _discover_recording_paths(base_dir, mediamtx_path, rtmp_key)


def _build_mp4_from_paths(paths: List[str], stream_id: str) -> Optional[str]:
    if not paths:
        return None
    out_mp4 = os.path.join("/tmp", f"stream-archive-{stream_id}.mp4")
    try:
        if len(paths) == 1 and paths[0].lower().endswith(".mp4"):
            if paths[0] != out_mp4:
                shutil.copy2(paths[0], out_mp4)
            else:
                out_mp4 = paths[0]
        elif len(paths) == 1:
            subprocess.run(
                ["ffmpeg", "-y", "-i", paths[0], "-c", "copy", out_mp4],
                check=False,
                capture_output=True,
                timeout=3600,
            )
        else:
            lst = "/tmp/concat-" + str(uuid_lib.uuid4()) + ".txt"
            with open(lst, "w", encoding="utf-8") as fh:
                for p in sorted(paths):
                    safe = p.replace("'", "'\\''")
                    fh.write(f"file '{safe}'\n")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out_mp4],
                check=False,
                capture_output=True,
                timeout=3600,
            )
            try:
                os.remove(lst)
            except OSError:
                pass
    except Exception as e:
        logger.error("ffmpeg error: %s", e)
        out_mp4 = paths[0]

    if os.path.isfile(out_mp4) and os.path.getsize(out_mp4) >= 2048:
        return out_mp4
    if paths and os.path.isfile(paths[0]) and os.path.getsize(paths[0]) >= 2048:
        return paths[0]
    return None


async def _set_archive_state(
    stream_id: str,
    archive_status: str,
    archive_error: Optional[str] = None,
    archived_video_id: Optional[str] = None,
):
    async with async_session() as db:
        await Stream.update_status(
            db,
            stream_id,
            archive_status=archive_status,
            archive_error=archive_error,
            archived_video_id=archived_video_id,
        )


def _seconds_since(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        end = dt.replace(tzinfo=timezone.utc)
    else:
        end = dt.astimezone(timezone.utc)
    return (now - end).total_seconds()


async def _fetch_video_status(video_id: str) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {settings.internal_auth_token}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.video_service_url}/internal/videos/{video_id}/status",
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return {"missing": True}
    except httpx.RequestError as e:
        logger.warning("video status fetch failed: %s", e)
    return None


def _archive_status_idle(st: Optional[str]) -> bool:
    return st in (None, "", "idle")


async def _resolve_stale_archive(stream: Stream, db: AsyncSession) -> Stream:
    """Зависшая архивация → failed; «сирота» без статуса после эфира → сброс в idle."""
    st = getattr(stream, "archive_status", None)
    vid = stream.archived_video_id
    if not stream.end_time or vid:
        return stream

    in_progress = st in ("pending", "waiting_recording", "uploading")
    orphan = _archive_status_idle(st)
    if not in_progress and not orphan:
        return stream

    age = _seconds_since(stream.end_time)
    if age is None or age < settings.archive_stale_seconds:
        return stream

    if orphan:
        await Stream.reset_archive(db, str(stream.id))
        refreshed = await Stream.get_by_id(db, str(stream.id))
        return refreshed or stream

    msg = (
        "Превышено время ожидания файла записи. Остановите OBS, проверьте MediaMTX "
        "или нажмите «Сбросить и начать заново»."
    )
    await Stream.update_status(db, str(stream.id), archive_status="failed", archive_error=msg)
    refreshed = await Stream.get_by_id(db, str(stream.id))
    return refreshed or stream


async def build_archive_payload(stream: Stream, db: AsyncSession) -> Dict[str, Any]:
    """
    phase: idle | pending | waiting_recording | uploading | transcoding | ready | failed
    progress: 0-100 для UI
    """
    if not _stream_saves_recording(stream):
        return {"phase": "idle", "progress": 0, "video_id": None, "error": None, "video_status": None}

    stream = await _resolve_stale_archive(stream, db)
    st = getattr(stream, "archive_status", None) or "idle"
    err = getattr(stream, "archive_error", None)
    vid = str(stream.archived_video_id) if stream.archived_video_id else None

    if not stream.end_time and not vid and st in (None, "idle"):
        return {"phase": "idle", "progress": 0, "video_id": None, "error": None, "video_status": None}

    if st == "failed":
        return {"phase": "failed", "progress": 0, "video_id": vid, "error": err or "Не удалось сохранить запись", "video_status": None}

    if vid:
        vs = await _fetch_video_status(vid)
        if vs and vs.get("missing"):
            await Stream.reset_archive(db, str(stream.id))
            return {
                "phase": "idle",
                "progress": 0,
                "video_id": None,
                "error": None,
                "video_status": None,
            }
        if vs:
            status = vs.get("status") or "uploaded"
            progress = int(vs.get("transcoding_progress") or 0)
            if status == "ready":
                return {
                    "phase": "ready",
                    "progress": 100,
                    "video_id": vid,
                    "error": None,
                    "video_status": status,
                    "video_title": vs.get("title"),
                }
            if status == "failed":
                return {
                    "phase": "failed",
                    "progress": progress,
                    "video_id": vid,
                    "error": "Ошибка кодирования видео",
                    "video_status": status,
                }
            return {
                "phase": "transcoding",
                "progress": max(15, min(progress, 99)),
                "video_id": vid,
                "error": None,
                "video_status": status,
            }
        return {"phase": "transcoding", "progress": 20, "video_id": vid, "error": None, "video_status": "transcoding"}

    phase_map = {
        "pending": ("pending", 5),
        "waiting_recording": ("waiting_recording", 12),
        "uploading": ("uploading", 25),
        "completed": ("transcoding", 30),
    }
    if st in phase_map:
        phase, progress = phase_map[st]
        return {"phase": phase, "progress": progress, "video_id": None, "error": None, "video_status": None}

    if stream.end_time and not vid:
        if _archive_status_idle(st):
            age = _seconds_since(stream.end_time)
            if age is not None and age < settings.archive_stale_seconds:
                return {
                    "phase": "waiting_recording",
                    "progress": 10,
                    "video_id": None,
                    "error": None,
                    "video_status": None,
                }
            return {"phase": "idle", "progress": 0, "video_id": None, "error": None, "video_status": None}
        return {"phase": "idle", "progress": 0, "video_id": None, "error": err, "video_status": None}

    return {"phase": "idle", "progress": 0, "video_id": vid, "error": err, "video_status": None}


def _enqueue_archive_task(stream_id: str, background_tasks: Optional[BackgroundTasks] = None) -> None:
    if background_tasks is not None:
        background_tasks.add_task(archive_stream_task, stream_id)
    else:
        asyncio.create_task(archive_stream_task(stream_id))


async def _schedule_archive_if_needed(
    stream_id: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    if stream_id in _archive_tasks_inflight:
        return
    async with async_session() as db:
        stream = await Stream.get_by_id(db, stream_id)
        if not stream or not _stream_saves_recording(stream) or stream.archived_video_id:
            return
        st = getattr(stream, "archive_status", None)
        if st in ("pending", "waiting_recording", "uploading", "completed"):
            return
        await Stream.update_status(
            db, stream_id, archive_status="pending", archive_error=None
        )
    _enqueue_archive_task(stream_id, background_tasks)


async def _mediamtx_path_has_publisher(path_name: str) -> Optional[bool]:
    """True — RTMP идёт, False — пути нет, None — API недоступен."""
    encoded = quote(path_name, safe="")
    url = f"{settings.mediamtx_api_url.rstrip('/')}/v3/paths/get/{encoded}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
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


async def _finalize_stream_session(
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
    await _schedule_archive_if_needed(str(stream.id), background_tasks)


async def _reconcile_stream_rtmp_state(
    db: AsyncSession,
    stream: Stream,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Stream:
    if stream.end_time is not None:
        return stream
    if not stream.is_live and not stream.start_time:
        return stream

    path = getattr(stream, "mediamtx_path", None) or _mediamtx_path(stream.rtmp_key)
    publishing = await _mediamtx_path_has_publisher(path)
    if publishing is None or publishing:
        return stream

    logger.info("RTMP reconcile: finalize stream %s (path %s offline)", stream.id, path)
    await _finalize_stream_session(db, stream, background_tasks)
    refreshed = await Stream.get_by_id(db, str(stream.id))
    return refreshed or stream


async def _notify_stream_live(stream: Stream, channel_id: str, channel_name: str, channel_handle: Optional[str]):
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
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{settings.notification_service_url}/internal/events/channel",
                json=payload,
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
            )
            if r.status_code != 200:
                logger.warning("stream_live notify failed: %s %s", r.status_code, r.text)
            else:
                logger.info("stream_live notify: %s", r.json())
    except httpx.RequestError as e:
        logger.warning("stream_live notify error: %s", e)


async def _mark_stream_live_on_rtmp_publish(db: AsyncSession, rtmp_key: str) -> Optional[Stream]:
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

    was_already_live = bool(stream.is_live)
    now = datetime.utcnow()
    await Stream.update_status(
        db,
        str(stream.id),
        is_live=True,
        start_time=stream.start_time or now,
    )
    refreshed = await Stream.get_by_id(db, str(stream.id))
    if refreshed and not was_already_live:
        channel_id, channel_handle = await get_channel_for_owner(db, str(refreshed.user_id))
        if channel_id:
            channel_name = ""
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    ch = await client.get(
                        f"{settings.video_service_url}/internal/channels/by-owner/{refreshed.user_id}",
                        headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
                    )
                    if ch.status_code == 200:
                        channel_name = ch.json().get("name") or ""
                        channel_handle = ch.json().get("handle") or channel_handle
            except httpx.RequestError:
                pass
            await _notify_stream_live(refreshed, channel_id, channel_name, channel_handle)
    return refreshed


async def _finalize_stream_on_rtmp_disconnect(
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
    await _finalize_stream_session(db, stream, background_tasks)


@app.post("/internal/mediamtx/auth")
async def mediamtx_auth(request: Request, db: AsyncSession = Depends(get_db)):
    """MediaMTX HTTP authentication (publish only)."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    action = body.get("action", "")
    path = (body.get("path") or "").strip("/")
    logger.info("MediaMTX auth: action=%s path=%s", action, path)

    if action != "publish":
        return {"status": "ok"}

    key = _rtmp_key_from_mediamtx_path(path)
    if not key:
        raise HTTPException(status_code=401, detail="missing stream key")

    stream = await _mark_stream_live_on_rtmp_publish(db, key)
    if not stream:
        raise HTTPException(status_code=401, detail="stream not available for publish")

    return {"status": "ok"}


@app.get("/internal/mediamtx/ready")
async def mediamtx_ready(path: str, db: AsyncSession = Depends(get_db)):
    """MediaMTX runOnReady: RTMP-публикатор подключился, поток готов."""
    key = _rtmp_key_from_mediamtx_path(path)
    if not key:
        return {"ok": True}
    stream = await _mark_stream_live_on_rtmp_publish(db, key)
    if stream:
        logger.info("RTMP live: stream_id=%s key=%s", stream.id, key)
    return {"ok": True}


@app.get("/internal/mediamtx/not-ready")
async def mediamtx_not_ready(
    path: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """MediaMTX runOnNotReady: RTMP-публикатор отключился."""
    key = _rtmp_key_from_mediamtx_path(path)
    if not key:
        return {"ok": True}
    logger.info("RTMP disconnect: key=%s", key)
    await _finalize_stream_on_rtmp_disconnect(db, key, background_tasks)
    return {"ok": True}


async def archive_stream_task(stream_id: str):
    if stream_id in _archive_tasks_inflight:
        logger.info("Archive already running for stream %s", stream_id)
        return
    _archive_tasks_inflight.add(stream_id)
    try:
        await _archive_stream_task_impl(stream_id)
    finally:
        _archive_tasks_inflight.discard(stream_id)


async def _archive_stream_task_impl(stream_id: str):
    async with async_session() as db:
        stream = await Stream.get_by_id(db, stream_id)
        if not stream or not _stream_saves_recording(stream) or stream.archived_video_id:
            return
        st = getattr(stream, "archive_status", None)
        if st == "uploading":
            return
        invited = await list_stream_viewer_ids(db, stream_id)
        key = stream.rtmp_key
        mediamtx_path = getattr(stream, "mediamtx_path", None) or _mediamtx_path(key)
        user_id = str(stream.user_id)
        title = stream.title
        description = stream.description or ""
        visibility = getattr(stream, "visibility", None) or ("private" if stream.is_private else "dgi_employees")

    await _set_archive_state(stream_id, "waiting_recording", archive_error=None)

    base_dir = settings.recordings_path
    paths = await _wait_for_stable_recordings(base_dir, mediamtx_path, key)

    if not paths:
        await _set_archive_state(
            stream_id,
            "failed",
            archive_error="Файл записи не найден. Остановите трансляцию в OBS и подождите несколько секунд.",
        )
        logger.warning("No recording files for stream %s (path=%s)", stream_id, mediamtx_path)
        return

    out_mp4 = _build_mp4_from_paths(paths, stream_id)
    if not out_mp4:
        await _set_archive_state(
            stream_id,
            "failed",
            archive_error="Запись слишком мала или повреждена.",
        )
        return

    await _set_archive_state(stream_id, "uploading", archive_error=None)

    is_restricted = visibility == "private"
    classification = "restricted" if is_restricted else "internal"
    invited_csv = ",".join(invited)

    try:
        with open(out_mp4, "rb") as fh:
            file_data = fh.read()
    except OSError as e:
        logger.error("Cannot read recording: %s", e)
        await _set_archive_state(stream_id, "failed", archive_error="Не удалось прочитать файл записи")
        return

    data = {
        "user_id": user_id,
        "title": f"Запись эфира: {title}",
        "description": description,
        "classification": classification,
        "is_private": str(is_restricted).lower(),
        "invited_user_ids": invited_csv,
    }
    files = {"file": ("live-recording.mp4", file_data, "video/mp4")}

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                f"{settings.video_service_url}/internal/videos/from-recording",
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
                data=data,
                files=files,
            )
            if resp.status_code != 200:
                logger.error("Archive upload failed: %s %s", resp.status_code, resp.text)
                await _set_archive_state(
                    stream_id,
                    "failed",
                    archive_error=f"Ошибка загрузки на видеохостинг ({resp.status_code})",
                )
                return
            payload = resp.json()
            vid = payload.get("video_id")
            if vid:
                await _set_archive_state(
                    stream_id,
                    "completed",
                    archived_video_id=vid,
                    archive_error=None,
                )
                async with async_session() as db:
                    moved = await transfer_stream_likes_to_video(db, stream_id, vid)
                    logger.info(
                        "Stream %s archived as video %s; transferred %s likes",
                        stream_id,
                        vid,
                        moved,
                    )
                logger.info("Stream %s archived as video %s", stream_id, vid)
            else:
                await _set_archive_state(stream_id, "failed", archive_error="Видеохостинг не вернул id видео")
    except httpx.RequestError as e:
        logger.error("Archive upload request failed: %s", e)
        await _set_archive_state(stream_id, "failed", archive_error="Сервис видео недоступен")


@app.get("/streams/live")
async def get_live_streams_public_filtered(
    db: AsyncSession = Depends(get_db),
    profile: Optional[dict] = Depends(get_optional_profile),
):
    """Список активных эфиров с учётом видимости (сотрудники ДГИ / приватные приглашённые)."""
    rows = await Stream.get_live_streams(db)
    visible: List[Stream] = []
    for s in rows:
        if await _can_view_stream_db(db, s, profile):
            visible.append(s)
    owner_names = await _resolve_owner_usernames({str(s.user_id) for s in visible})
    items: List[dict] = []
    for s in visible:
        r = to_stream_response(s)
        uid = str(s.user_id)
        sid = str(s.id)
        likes_count, _ = await _stream_likes_state(db, s, None)
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
            }
        )
    return {"streams": items}


async def _go_live_archive_item(stream: Stream, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Элемент списка фоновых архиваций для go-live (или None, если уже готово/не показывать)."""
    if not _stream_saves_recording(stream):
        return None
    archive = await build_archive_payload(stream, db)
    phase = archive.get("phase") or "idle"
    if phase == "ready":
        await Stream.reset_archive(db, str(stream.id))
        return None
    if phase in ARCHIVE_BLOCKING_PHASES:
        return {
            "stream_id": str(stream.id),
            "title": stream.title,
            **archive,
        }
    return None


@app.post("/streams", response_model=StreamResponse)
async def create_stream(
    stream_data: StreamCreate,
    user_id: str = Depends(require_permission("video:stream")),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_channel_exists(user_id)
    open_session = await Stream.get_open_session_for_owner(db, user_id)
    if open_session:
        raise HTTPException(
            status_code=409,
            detail="Сначала завершите или отмените текущую подготовку трансляции",
        )

    rtmp_key = str(uuid_lib.uuid4()).replace("-", "")[:16]
    mediamtx_path = _mediamtx_path(rtmp_key)
    hls_url = _build_public_hls(mediamtx_path)

    stream = await Stream.create(
        db,
        **{
            "title": stream_data.title,
            "description": stream_data.description,
            "user_id": user_id,
            "rtmp_key": rtmp_key,
            "hls_url": hls_url,
            "visibility": stream_data.visibility,
            "mediamtx_path": mediamtx_path,
            "save_recording": stream_data.save_recording,
        },
    )
    if stream_data.visibility == "private" and stream_data.allowed_user_ids:
        await replace_stream_viewers(db, str(stream.id), stream_data.allowed_user_ids)

    return to_stream_response(stream)


@app.get("/streams/my-active")
async def get_my_active_stream(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    go-live: активная подготовка/эфир + список фоновых архиваций (не блокируют новый эфир).
    """
    active = await Stream.get_open_session_for_owner(db, user_id)
    if active:
        active = await _reconcile_stream_rtmp_state(db, active)
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
        item = await _go_live_archive_item(ended, db)
        if item:
            archiving_items.append(item)

    return {
        "stream": active_payload,
        "rtmp_state": rtmp_state,
        "archiving": archiving_items,
    }


@app.get("/streams/{stream_id}/archive-status")
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


@app.post("/streams/{stream_id}/archive/dismiss")
async def dismiss_stream_archive(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Сбросить зависшую обработку записи (после удаления видео или ошибки)."""
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    await Stream.reset_archive(db, stream_id)
    return {"message": "Состояние архивации сброшено", "archive": {"phase": "idle", "progress": 0, "video_id": None}}


@app.post("/streams/{stream_id}/archive/retry")
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
    if not _stream_saves_recording(stream):
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
    await _schedule_archive_if_needed(stream_id, background_tasks)
    return {"message": "Повторное сохранение запущено в фоне"}


@app.get("/streams", response_model=List[StreamResponse])
async def list_streams(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    streams = await Stream.get_all(db, user_id=user_id)
    return [to_stream_response(s) for s in streams]


@app.get("/streams/{stream_id}", response_model=StreamDetailResponse)
async def get_stream(
    stream_id: str,
    profile: Optional[dict] = Depends(get_optional_profile),
    db: AsyncSession = Depends(get_db),
):
    stream = await _require_stream_view_access(db, stream_id, profile)
    if stream.end_time is None and (stream.is_live or stream.start_time):
        stream = await _reconcile_stream_rtmp_state(db, stream)
        stream = await Stream.get_by_id(db, stream_id) or stream
    return await _build_stream_detail(db, stream, profile)


@app.post("/streams/{stream_id}/presence")
async def stream_presence_heartbeat(
    stream_id: str,
    profile: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db),
):
    stream = await _require_stream_view_access(db, stream_id, profile)
    touch_presence(str(stream.id), str(profile["id"]))
    return {"viewers_count": count_viewers(str(stream.id))}


@app.post("/streams/{stream_id}/presence/leave")
async def stream_presence_leave(
    stream_id: str,
    profile: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db),
):
    stream = await _require_stream_view_access(db, stream_id, profile)
    leave_presence(str(stream.id), str(profile["id"]))
    return {"viewers_count": count_viewers(str(stream.id))}


@app.post("/streams/{stream_id}/like")
async def like_stream(
    stream_id: str,
    profile: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db),
):
    stream = await _require_stream_view_access(db, stream_id, profile)
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
    likes_count, user_liked = await _stream_likes_state(db, stream, user_id)
    return {"likes_count": likes_count, "user_liked": user_liked}


@app.delete("/streams/{stream_id}/like")
async def unlike_stream(
    stream_id: str,
    profile: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db),
):
    stream = await _require_stream_view_access(db, stream_id, profile)
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
    likes_count, user_liked = await _stream_likes_state(db, stream, user_id)
    return {"likes_count": likes_count, "user_liked": user_liked}


@app.put("/streams/{stream_id}/start")
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


@app.post("/streams/{stream_id}/cancel")
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

    await Stream.update_status(db, stream_id, is_live=False, end_time=datetime.utcnow())
    return {"message": "Подготовка отменена"}


@app.put("/streams/{stream_id}/stop")
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


@app.websocket("/ws/streams/{stream_id}")
async def stream_websocket(websocket: WebSocket, stream_id: str):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping", "stream_id": stream_id})
    except WebSocketDisconnect:
        logger.info("WS disconnected %s", stream_id)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
