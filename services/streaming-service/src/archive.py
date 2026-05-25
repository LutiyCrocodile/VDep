"""Post-stream recording archive pipeline."""
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
from .stream_helpers import mediamtx_path as build_mediamtx_path, stream_saves_recording

logger = logging.getLogger(__name__)

def collect_media_files(directory: str) -> List[str]:
    found: List[str] = []
    if not directory or not os.path.isdir(directory):
        return found
    for root, _, files in os.walk(directory):
        for name in files:
            lower = name.lower()
            if any(lower.endswith(s) for s in RECORDING_SUFFIXES):
                found.append(os.path.join(root, name))
    return found


def discover_recording_paths(base_dir: str, mediamtx_path: str, rtmp_key: str) -> List[str]:
    candidates: List[str] = []
    if mediamtx_path:
        preferred = os.path.join(base_dir, *mediamtx_path.split("/"))
        candidates.extend(collect_media_files(preferred))
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


async def wait_for_stable_recordings(
    base_dir: str, mediamtx_path: str, rtmp_key: str, attempts: int = 45, pause_sec: float = 2.0
) -> List[str]:
    """Ждём появления файла записи MediaMTX и стабильного размера (конец эфира)."""
    last_sizes: Dict[str, int] = {}
    for _ in range(attempts):
        paths = discover_recording_paths(base_dir, mediamtx_path, rtmp_key)
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
    return discover_recording_paths(base_dir, mediamtx_path, rtmp_key)


def build_mp4_from_paths(paths: List[str], stream_id: str) -> Optional[str]:
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


async def set_archive_state(
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


def seconds_since(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        end = dt.replace(tzinfo=timezone.utc)
    else:
        end = dt.astimezone(timezone.utc)
    return (now - end).total_seconds()


async def fetch_video_status(video_id: str) -> Optional[Dict[str, Any]]:
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


def archive_status_idle(st: Optional[str]) -> bool:
    return st in (None, "", "idle")


async def resolve_stale_archive(stream: Stream, db: AsyncSession) -> Stream:
    """Зависшая архивация → failed; «сирота» без статуса после эфира → сброс в idle."""
    st = getattr(stream, "archive_status", None)
    vid = stream.archived_video_id
    if not stream.end_time or vid:
        return stream

    in_progress = st in ("pending", "waiting_recording", "uploading")
    orphan = archive_status_idle(st)
    if not in_progress and not orphan:
        return stream

    age = seconds_since(stream.end_time)
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
    if not stream_saves_recording(stream):
        return {"phase": "idle", "progress": 0, "video_id": None, "error": None, "video_status": None}

    stream = await resolve_stale_archive(stream, db)
    st = getattr(stream, "archive_status", None) or "idle"
    err = getattr(stream, "archive_error", None)
    vid = str(stream.archived_video_id) if stream.archived_video_id else None

    if not stream.end_time:
        return {"phase": "idle", "progress": 0, "video_id": None, "error": None, "video_status": None}

    if st == "failed":
        return {"phase": "failed", "progress": 0, "video_id": vid, "error": err or "Не удалось сохранить запись", "video_status": None}

    if vid:
        vs = await fetch_video_status(vid)
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
        if archive_status_idle(st):
            age = seconds_since(stream.end_time)
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


def enqueue_archive_task(stream_id: str, background_tasks: Optional[BackgroundTasks] = None) -> None:
    if background_tasks is not None:
        background_tasks.add_task(archive_stream_task, stream_id)
    else:
        asyncio.create_task(archive_stream_task(stream_id))


async def schedule_archive_if_needed(
    stream_id: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    if stream_id in _archive_tasks_inflight:
        return
    async with async_session() as db:
        stream = await Stream.get_by_id(db, stream_id)
        if not stream or not stream_saves_recording(stream) or stream.archived_video_id:
            return
        if stream.end_time is None or stream.is_live:
            return
        st = getattr(stream, "archive_status", None)
        if st in ("pending", "waiting_recording", "uploading", "completed"):
            return
        await Stream.update_status(
            db, stream_id, archive_status="pending", archive_error=None
        )
    enqueue_archive_task(stream_id, background_tasks)


async def archive_stream_task(stream_id: str):
    if stream_id in _archive_tasks_inflight:
        logger.info("Archive already running for stream %s", stream_id)
        return
    _archive_tasks_inflight.add(stream_id)
    try:
        await archive_stream_task_impl(stream_id)
    finally:
        _archive_tasks_inflight.discard(stream_id)


async def archive_stream_task_impl(stream_id: str):
    async with async_session() as db:
        stream = await Stream.get_by_id(db, stream_id)
        if not stream or not stream_saves_recording(stream) or stream.archived_video_id:
            return
        if stream.end_time is None or stream.is_live:
            logger.info("Archive deferred for stream %s (still live)", stream_id)
            if getattr(stream, "archive_status", None) in ("pending", "waiting_recording"):
                await Stream.update_status(
                    db, stream_id, archive_status="idle", archive_error=None
                )
            return
        st = getattr(stream, "archive_status", None)
        if st == "uploading":
            return
        invited = await list_stream_viewer_ids(db, stream_id)
        key = stream.rtmp_key
        mtx_path = getattr(stream, "mediamtx_path", None) or build_mediamtx_path(key)
        user_id = str(stream.user_id)
        title = stream.title
        description = stream.description or ""
        visibility = getattr(stream, "visibility", None) or ("private" if stream.is_private else "dgi_employees")

    await set_archive_state(stream_id, "waiting_recording", archive_error=None)

    base_dir = settings.recordings_path
    paths = await wait_for_stable_recordings(base_dir, mtx_path, key)

    if not paths:
        await set_archive_state(
            stream_id,
            "failed",
            archive_error="Файл записи не найден. Остановите трансляцию в OBS и подождите несколько секунд.",
        )
        logger.warning("No recording files for stream %s (path=%s)", stream_id, mtx_path)
        return

    out_mp4 = build_mp4_from_paths(paths, stream_id)
    if not out_mp4:
        await set_archive_state(
            stream_id,
            "failed",
            archive_error="Запись слишком мала или повреждена.",
        )
        return

    await set_archive_state(stream_id, "uploading", archive_error=None)

    is_restricted = visibility == "private"
    classification = "restricted" if is_restricted else "internal"
    invited_csv = ",".join(invited)

    try:
        with open(out_mp4, "rb") as fh:
            file_data = fh.read()
    except OSError as e:
        logger.error("Cannot read recording: %s", e)
        await set_archive_state(stream_id, "failed", archive_error="Не удалось прочитать файл записи")
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
                await set_archive_state(
                    stream_id,
                    "failed",
                    archive_error=f"Ошибка загрузки на видеохостинг ({resp.status_code})",
                )
                return
            payload = resp.json()
            vid = payload.get("video_id")
            if vid:
                await set_archive_state(
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
                await set_archive_state(stream_id, "failed", archive_error="Видеохостинг не вернул id видео")
    except httpx.RequestError as e:
        logger.error("Archive upload request failed: %s", e)
        await set_archive_state(stream_id, "failed", archive_error="Сервис видео недоступен")


async def go_live_archive_item(stream: Stream, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Элемент списка фоновых архиваций для go-live (или None, если уже готово/не показывать)."""
    if stream.end_time is None:
        return None
    if not stream_saves_recording(stream):
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
