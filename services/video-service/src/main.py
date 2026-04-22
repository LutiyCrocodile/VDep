from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import hashlib
from datetime import datetime
import httpx
import json
from minio import Minio
from minio.error import S3Error
import subprocess
import logging

from .database import get_db, create_tables
from .models import Video
from .config import settings
from .celery_app import celery_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MinIO client
minio_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure
)

# Security
security = HTTPBearer()

class VideoUploadResponse(BaseModel):
    video_id: str
    upload_url: str
    minio_key: str

class VideoResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    duration: Optional[str]
    resolution: Optional[str]
    bitrate: Optional[int]
    file_size: int
    status: str
    hls_playlist_url: Optional[str]
    is_private: bool
    tags: List[str]
    created_at: datetime
    user_id: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    # Ensure MinIO bucket exists
    try:
        if not minio_client.bucket_exists(settings.minio_bucket):
            minio_client.make_bucket(settings.minio_bucket)
            logger.info(f"Created MinIO bucket: {settings.minio_bucket}")
    except S3Error as e:
        logger.error(f"MinIO error: {e}")
    logger.info("Video service started")
    yield
    # Shutdown
    logger.info("Video service shutting down")

app = FastAPI(title="Video Service", version="1.0.0", lifespan=lifespan)

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

def generate_minio_key(video_id: str, filename: str) -> str:
    file_hash = hashlib.sha256(f"{video_id}{filename}".encode()).hexdigest()[:16]
    return f"{video_id}/{file_hash}"

@app.post("/videos/upload/init", response_model=VideoUploadResponse)
async def init_upload(
    title: str = Form(...),
    description: str = Form(""),
    is_private: bool = Form(False),
    tags: str = Form(""),  # JSON array as string
    filename: str = Form(...),
    file_size: int = Form(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Parse tags
    try:
        tags_list = json.loads(tags) if tags else []
    except json.JSONDecodeError:
        tags_list = []

    # Create video record
    video_id = str(uuid.uuid4())
    minio_key = generate_minio_key(video_id, filename)

    video = await Video.create(db, **{
        "id": video_id,
        "title": title,
        "description": description,
        "user_id": user_id,
        "file_size": file_size,
        "minio_key": minio_key,
        "status": "uploading",
        "is_private": is_private,
        "tags": tags_list
    })

    # Generate presigned URL for upload
    try:
        upload_url = minio_client.presigned_put_object(
            settings.minio_bucket,
            minio_key,
            expires=settings.upload_expiry_seconds
        )
    except S3Error as e:
        logger.error(f"MinIO presigned URL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")

    return VideoUploadResponse(
        video_id=video_id,
        upload_url=upload_url,
        minio_key=minio_key
    )

@app.post("/videos/{video_id}/complete")
async def complete_upload(
    video_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Verify video ownership
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")

    # Update status
    await Video.update_status(db, video_id, "uploaded")

    # Start transcoding in background
    background_tasks.add_task(start_transcoding, video_id, video.minio_key)

    return {"message": "Upload completed, transcoding started"}

def start_transcoding(video_id: str, minio_key: str):
    # Send task to Celery
    celery_app.send_task(
        "video_service.tasks.transcode_video",
        args=[video_id, minio_key],
        queue="video_transcoding"
    )

@app.get("/videos", response_model=List[VideoResponse])
async def list_videos(
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    videos = await Video.get_all(db, skip=skip, limit=limit, user_id=user_id)
    return [
        VideoResponse(
            id=str(v.id),
            title=v.title,
            description=v.description,
            duration=str(v.duration) if v.duration else None,
            resolution=v.resolution,
            bitrate=v.bitrate,
            file_size=v.file_size,
            status=v.status,
            hls_playlist_url=v.hls_playlist_url,
            is_private=v.is_private,
            tags=v.tags or [],
            created_at=v.created_at,
            user_id=str(v.user_id)
        ) for v in videos
    ]

@app.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check permissions for private videos
    if video.is_private and (not user_id or str(video.user_id) != user_id):
        # Check if user has permission to view private videos
        if not await check_private_video_permission(user_id, video.user_id):
            raise HTTPException(status_code=403, detail="Access denied")

    return VideoResponse(
        id=str(video.id),
        title=video.title,
        description=video.description,
        duration=str(video.duration) if video.duration else None,
        resolution=video.resolution,
        bitrate=video.bitrate,
        file_size=video.file_size,
        status=video.status,
        hls_playlist_url=video.hls_playlist_url,
        is_private=video.is_private,
        tags=video.tags or [],
        created_at=video.created_at,
        user_id=str(video.user_id)
    )

async def check_private_video_permission(viewer_id: str, owner_id: str) -> bool:
    # Check if viewer has 'view_private_videos' permission
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.auth_service_url}/users/{viewer_id}/permissions",
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"}
            )
            if response.status_code == 200:
                permissions = response.json()
                return "view_private_videos" in permissions
        except httpx.RequestError:
            pass
    return False

@app.get("/videos/{video_id}/signed-url")
async def get_signed_url(
    video_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check permissions
    if video.is_private and (not user_id or str(video.user_id) != user_id):
        if not await check_private_video_permission(user_id, video.user_id):
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        signed_url = minio_client.presigned_get_object(
            settings.minio_bucket,
            video.minio_key,
            expires=settings.signed_url_expiry_seconds
        )
        return {"signed_url": signed_url}
    except S3Error as e:
        logger.error(f"MinIO signed URL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate signed URL")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
