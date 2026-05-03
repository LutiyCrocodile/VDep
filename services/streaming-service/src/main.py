from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import asyncio
import logging
from datetime import datetime
import httpx
import subprocess
import json

from .database import get_db, create_tables, Stream
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

class StreamCreate(BaseModel):
    title: str
    description: str = ""
    is_private: bool = False

class StreamResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    rtmp_key: str
    hls_url: Optional[str]
    is_live: bool
    start_time: Optional[datetime]
    user_id: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    logger.info("Streaming service started")
    yield
    # Shutdown
    logger.info("Streaming service shutting down")

app = FastAPI(title="Streaming Service", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Validate token with auth service
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.auth_service_url}/users/me",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                return user_data["id"]
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")

@app.post("/streams", response_model=StreamResponse)
async def create_stream(
    stream_data: StreamCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Check if user has a channel
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.video_service_url}/channels/my",
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=403, detail="You must create a channel before starting streams")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Video service unavailable")

    # Generate RTMP key
    rtmp_key = str(uuid.uuid4()).replace('-', '')[:16]

    # Generate HLS URL
    hls_url = f"/hls/{rtmp_key}/index.m3u8"

    # Create stream record
    stream = await Stream.create(db, **{
        "title": stream_data.title,
        "description": stream_data.description,
        "user_id": user_id,
        "rtmp_key": rtmp_key,
        "hls_url": hls_url,
        "is_private": stream_data.is_private
    })

    return StreamResponse(
        id=str(stream.id),
        title=stream.title,
        description=stream.description,
        rtmp_key=stream.rtmp_key,
        hls_url=stream.hls_url,
        is_live=stream.is_live,
        start_time=stream.start_time,
        user_id=str(stream.user_id)
    )

@app.get("/streams", response_model=List[StreamResponse])
async def list_streams(
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    streams = await Stream.get_all(db, user_id=user_id)
    return [
        StreamResponse(
            id=str(s.id),
            title=s.title,
            description=s.description,
            rtmp_key=s.rtmp_key,
            hls_url=s.hls_url,
            is_live=s.is_live,
            start_time=s.start_time,
            user_id=str(s.user_id)
        ) for s in streams
    ]

@app.get("/streams/{stream_id}", response_model=StreamResponse)
async def get_stream(
    stream_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    stream = await Stream.get_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Check permissions for private streams
    if stream.is_private and (not user_id or str(stream.user_id) != user_id):
        if not await check_private_stream_permission(user_id, stream.user_id):
            raise HTTPException(status_code=403, detail="Access denied")

    return StreamResponse(
        id=str(stream.id),
        title=stream.title,
        description=stream.description,
        rtmp_key=stream.rtmp_key,
        hls_url=stream.hls_url,
        is_live=stream.is_live,
        start_time=stream.start_time,
        user_id=str(stream.user_id)
    )

async def check_private_stream_permission(viewer_id: str, owner_id: str) -> bool:
    # Check if viewer has 'manage_streams' permission
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.auth_service_url}/users/{viewer_id}/permissions",
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"}
            )
            if response.status_code == 200:
                permissions = response.json()
                return "manage_streams" in permissions
        except httpx.RequestError:
            pass
    return False

@app.put("/streams/{stream_id}/start")
async def start_stream(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Verify ownership
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Update stream status
    await Stream.update_status(db, stream_id, is_live=True, start_time=datetime.utcnow())

    # Send notification about stream start
    await send_notification(
        user_id,
        "stream_start",
        f"Трансляция '{stream.title}' началась",
        {"stream_id": stream_id}
    )

    return {"message": "Stream started"}

@app.put("/streams/{stream_id}/stop")
async def stop_stream(
    stream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Verify ownership
    stream = await Stream.get_by_id(db, stream_id)
    if not stream or str(stream.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Update stream status
    await Stream.update_status(db, stream_id, is_live=False, end_time=datetime.utcnow())

    # Archive the stream to video (placeholder)
    # In production, this would convert DVR segments to a video file
    archived_video_id = await archive_stream(stream_id)

    return {"message": "Stream stopped", "archived_video_id": archived_video_id}

async def archive_stream(stream_id: str) -> Optional[str]:
    """
    Archive stream by combining HLS segments into a video file
    """
    logger.info(f"Archiving stream {stream_id}")
    
    try:
        # Get stream info
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.video_service_url}/videos",
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"}
            )
        
        # Placeholder: In real implementation, this would:
        # 1. Download HLS segments from Nginx temp storage
        # 2. Combine them using FFmpeg
        # 3. Upload to MinIO
        # 4. Create video record
        # 5. Update stream with archived_video_id
        
        logger.info(f"Stream {stream_id} archived (placeholder)")
        return None
    except Exception as e:
        logger.error(f"Failed to archive stream {stream_id}: {e}")
        return None

async def send_notification(user_id: str, notification_type: str, message: str, data: dict = None):
    # Send notification via notification service
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{settings.notification_service_url}/notifications",
                json={
                    "user_id": user_id,
                    "type": notification_type,
                    "message": message,
                    "data": data
                },
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"}
            )
        except httpx.RequestError:
            logger.error("Failed to send notification")

# WebSocket endpoint for real-time stream status updates
@app.websocket("/ws/streams/{stream_id}")
async def stream_websocket(websocket: WebSocket, stream_id: str):
    await websocket.accept()

    # Subscribe to stream updates
    try:
        while True:
            # In production, this would listen to Redis pub/sub for stream events
            await asyncio.sleep(5)  # Placeholder
            # Send stream status updates
            await websocket.send_json({"type": "status", "stream_id": stream_id, "is_live": True})
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for stream {stream_id}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/streams/validate")
async def validate_stream_key(
    rtmp_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate RTMP stream key (called by Nginx on publish)
    """
    stream = await Stream.get_by_rtmp_key(db, rtmp_key)
    if not stream:
        raise HTTPException(status_code=403, detail="Invalid stream key")
    
    return {"valid": True, "stream_id": str(stream.id)}

@app.get("/streams/live")
async def get_live_streams(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all currently live streams
    """
    streams = await Stream.get_live_streams(db)
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "description": s.description,
            "hls_url": s.hls_url,
            "start_time": str(s.start_time) if s.start_time else None,
            "user_id": str(s.user_id)
        }
        for s in streams
    ]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
