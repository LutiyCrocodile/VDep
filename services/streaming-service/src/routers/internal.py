"""MediaMTX internal routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..rtmp import finalize_stream_on_rtmp_disconnect, mark_stream_live_on_rtmp_publish
from ..stream_helpers import rtmp_key_from_mediamtx_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/mediamtx")

@router.post("/auth")
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

    key = rtmp_key_from_mediamtx_path(path)
    if not key:
        raise HTTPException(status_code=401, detail="missing stream key")

    stream = await mark_stream_live_on_rtmp_publish(db, key)
    if not stream:
        raise HTTPException(status_code=401, detail="stream not available for publish")

    return {"status": "ok"}


@router.get("/ready")
async def mediamtx_ready(path: str, db: AsyncSession = Depends(get_db)):
    """MediaMTX runOnReady: RTMP-публикатор подключился, поток готов."""
    key = rtmp_key_from_mediamtx_path(path)
    if not key:
        return {"ok": True}
    stream = await mark_stream_live_on_rtmp_publish(db, key)
    if stream:
        logger.info("RTMP live: stream_id=%s key=%s", stream.id, key)
    return {"ok": True}


@router.get("/not-ready")
async def mediamtx_not_ready(
    path: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """MediaMTX runOnNotReady: RTMP-публикатор отключился."""
    key = rtmp_key_from_mediamtx_path(path)
    if not key:
        return {"ok": True}
    logger.info("RTMP disconnect: key=%s", key)
    await finalize_stream_on_rtmp_disconnect(db, key, background_tasks)
    return {"ok": True}
