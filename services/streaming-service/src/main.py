from contextlib import asynccontextmanager
import asyncio
import json
import logging
import os
import subprocess
import uuid as uuid_lib
from datetime import datetime
from typing import List, Optional, Set

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn

from .auth_client import auth_client
from .config import settings
from .database import (
    Stream,
    async_session,
    create_tables,
    get_db,
    is_stream_viewer,
    list_stream_viewer_ids,
    replace_stream_viewers,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    logger.info("Streaming service started")
    yield
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


class StreamResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    rtmp_key: str
    hls_url: Optional[str]
    is_live: bool
    start_time: Optional[datetime]
    user_id: str
    visibility: str = "dgi_employees"
    rtmp_server_url: str
    rtmp_stream_key: str


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
        user_id=str(s.user_id),
        visibility=vis,
        rtmp_server_url=_build_rtmp_server_url(),
        rtmp_stream_key=s.rtmp_key,
    )


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

    parts = path.split("/")
    key = parts[-1] if parts else ""
    if not key:
        raise HTTPException(status_code=401, detail="missing stream key")

    stream = await Stream.get_by_rtmp_key(db, key)
    if not stream or not stream.is_live:
        raise HTTPException(status_code=401, detail="stream not active")

    return {"status": "ok"}


@app.get("/internal/mediamtx/not-ready")
async def mediamtx_not_ready(
    path: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """MediaMTX runOnNotReady: publisher disconnected."""
    path = path.strip("/")
    parts = path.split("/")
    key = parts[-1] if parts else ""
    if not key:
        return {"ok": True}
    stream = await Stream.get_by_rtmp_key(db, key)
    if not stream:
        return {"ok": True}
    if stream.archived_video_id:
        return {"ok": True}
    await Stream.update_status(db, str(stream.id), is_live=False, end_time=datetime.utcnow())
    background_tasks.add_task(archive_stream_task, str(stream.id))
    return {"ok": True}


async def archive_stream_task(stream_id: str):
    async with async_session() as db:
        stream = await Stream.get_by_id(db, stream_id)
        if not stream or stream.archived_video_id:
            return
        invited = await list_stream_viewer_ids(db, stream_id)
        key = stream.rtmp_key
        user_id = str(stream.user_id)
        title = stream.title
        description = stream.description or ""
        visibility = getattr(stream, "visibility", None) or ("private" if stream.is_private else "dgi_employees")

    base_dir = settings.recordings_path
    candidates: List[str] = []
    if os.path.isdir(base_dir):
        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.endswith((".mp4", ".m4v", ".mpd", ".webm", ".ts", ".m4s")):
                    full = os.path.join(root, f)
                    candidates.append(full)

    narrowed = [p for p in candidates if key in p.replace(os.sep, "/")]
    paths = sorted(narrowed or candidates, key=os.path.getmtime, reverse=True) if (narrowed or candidates) else []

    if not paths:
        logger.warning("No recording files for stream %s", stream_id)
        return

    out_mp4 = os.path.join("/tmp", f"stream-archive-{stream_id}.mp4")
    try:
        if len(paths) == 1 and paths[0].endswith(".mp4"):
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
                    fh.write(f"file '{p}'\n")
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

    if not os.path.isfile(out_mp4) or os.path.getsize(out_mp4) < 2048:
        logger.warning("Recording too small; skip archive for %s", stream_id)
        return

    is_restricted = visibility == "private"
    classification = "restricted" if is_restricted else "internal"
    invited_csv = ",".join(invited)

    try:
        with open(out_mp4, "rb") as fh:
            file_data = fh.read()
    except OSError as e:
        logger.error("Cannot read recording: %s", e)
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

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{settings.video_service_url}/internal/videos/from-recording",
            headers={"Authorization": f"Bearer {settings.internal_auth_token}"},
            data=data,
            files=files,
        )
        if resp.status_code != 200:
            logger.error("Archive upload failed: %s %s", resp.status_code, resp.text)
            return
        payload = resp.json()
        vid = payload.get("video_id")
        if vid:
            async with async_session() as db:
                await Stream.update_status(db, stream_id, archived_video_id=vid)
            logger.info("Stream %s archived as video %s", stream_id, vid)


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
                "viewers_count": 0,
                "visibility": r.visibility,
            }
        )
    return {"streams": items}


@app.post("/streams", response_model=StreamResponse)
async def create_stream(
    stream_data: StreamCreate,
    user_id: str = Depends(require_permission("video:stream")),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_channel_exists(user_id)

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
    """Последняя трансляция пользователя (черновик или live), не заархивированная."""
    s = await Stream.get_latest_for_owner(db, user_id)
    if not s or s.archived_video_id:
        return {"stream": None}
    return {"stream": to_stream_response(s).model_dump()}


@app.get("/streams", response_model=List[StreamResponse])
async def list_streams(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    streams = await Stream.get_all(db, user_id=user_id)
    return [to_stream_response(s) for s in streams]


@app.get("/streams/{stream_id}", response_model=StreamResponse)
async def get_stream(
    stream_id: str,
    profile: Optional[dict] = Depends(get_optional_profile),
    db: AsyncSession = Depends(get_db),
):
    stream = await Stream.get_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")
    if not await _can_view_stream_db(db, stream, profile):
        raise HTTPException(status_code=403, detail="Нет доступа к трансляции")
    return to_stream_response(stream)


@app.put("/streams/{stream_id}/start")
async def start_stream(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")

    await Stream.update_status(db, stream_id, is_live=True, start_time=datetime.utcnow())
    return {"message": "Можно подключать OBS", "stream_id": stream_id}


@app.put("/streams/{stream_id}/stop")
async def stop_stream(
    stream_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Трансляция не найдена")

    await Stream.update_status(db, stream_id, is_live=False, end_time=datetime.utcnow())
    if not stream.archived_video_id:
        background_tasks.add_task(archive_stream_task, stream_id)
    return {"message": "Трансляция остановлена, идёт сохранение записи", "stream_id": stream_id}


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
