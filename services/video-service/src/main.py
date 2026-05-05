from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uvicorn
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import hashlib
import io
from datetime import datetime, timedelta
import httpx
import json
from minio import Minio
from minio.error import S3Error
import subprocess
import logging

from .database import get_db, create_tables, Video, Channel, Subscription
from .config import settings
from .celery_app import celery_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MinIO client (internal for service operations)
minio_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure
)

# Security
security = HTTPBearer(auto_error=False)

class VideoUploadResponse(BaseModel):
    video_id: str
    upload_url: str
    minio_key: str

class VideoResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    duration: Optional[int]  # Changed to int (seconds)
    resolution: Optional[str]
    bitrate: Optional[int]
    file_size: int
    status: str
    hls_playlist_url: Optional[str]
    thumbnail_url: Optional[str]
    is_private: bool
    tags: List[str]
    created_at: datetime
    user_id: str
    channel_id: Optional[str] = None
    views_count: int = 0
    owner_username: Optional[str] = None  # Channel name for display

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    handle: str
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None

class ChannelResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    handle: str
    avatar_url: Optional[str]
    banner_url: Optional[str]
    owner_id: str
    subscribers_count: int
    is_verified: bool
    created_at: datetime

class SubscriptionResponse(BaseModel):
    id: str
    subscriber_id: str
    channel_id: str
    created_at: datetime

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Validate token with auth service
    if not credentials:
        return None
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
                return None
        except httpx.RequestError:
            return None

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
    # Check if user has a channel
    channel = await Channel.get_by_owner(db, user_id)
    if not channel:
        raise HTTPException(status_code=403, detail="You must create a channel before uploading videos")

    # Parse tags
    try:
        tags_list = json.loads(tags) if tags else []
    except json.JSONDecodeError:
        tags_list = []

    # Create video record with channel_id
    video_id = str(uuid.uuid4())
    minio_key = generate_minio_key(video_id, filename)

    video = await Video.create(db, **{
        "id": video_id,
        "title": title,
        "description": description,
        "user_id": user_id,
        "channel_id": str(channel.id),
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
            expires=timedelta(seconds=settings.upload_expiry_seconds)
        )
    except S3Error as e:
        logger.error(f"MinIO presigned URL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")

    return VideoUploadResponse(
        video_id=video_id,
        upload_url=upload_url,
        minio_key=minio_key
    )

@app.post("/videos/{video_id}/upload-data")
async def upload_video_data(
    video_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Direct file upload endpoint - avoids CORS issues with MinIO"""
    # Verify video ownership
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status != "uploading":
        raise HTTPException(status_code=400, detail="Video already uploaded or processed")
    
    # Upload to MinIO
    try:
        file_size = 0
        # Read file in chunks
        chunk_size = 1024 * 1024  # 1MB chunks
        chunks = []
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
            file_size += len(chunk)
        
        file_data = b''.join(chunks)
        
        minio_client.put_object(
            settings.minio_bucket,
            video.minio_key,
            io.BytesIO(file_data),
            file_size,
            content_type=file.content_type or 'application/octet-stream'
        )
        
        logger.info(f"File uploaded to MinIO for video {video_id}, size: {file_size}")
        
        return {
            "message": "File uploaded successfully",
            "video_id": video_id,
            "file_size": file_size
        }
        
    except S3Error as e:
        logger.error(f"MinIO upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

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
        "src.tasks.transcode_video",
        args=[video_id, minio_key],
        queue="video_transcoding"
    )

def parse_duration(duration_val) -> Optional[int]:
    """Parse duration string like '45s' to integer seconds"""
    if not duration_val:
        return None
    if isinstance(duration_val, int):
        return duration_val
    if isinstance(duration_val, str):
        # Remove 's' suffix and convert to int
        return int(duration_val.rstrip('s'))
    return None

def get_thumbnail_url(thumbnail_path: str) -> str:
    """Convert thumbnail path to full URL"""
    if not thumbnail_path:
        return ""
    if thumbnail_path.startswith('http'):
        return thumbnail_path
    # Return direct URL to MinIO (bucket is now public)
    return f"http://localhost:9000/{settings.minio_bucket}{thumbnail_path}"

def get_playlist_url(playlist_path: str) -> str:
    """Convert playlist path to full URL accessible by frontend"""
    if not playlist_path:
        return ""
    if playlist_path.startswith('http'):
        return playlist_path
    # Return direct URL to MinIO (bucket is now public)
    return f"http://localhost:9000/{settings.minio_bucket}{playlist_path}"

@app.get("/videos", response_model=List[VideoResponse])
async def list_videos(
    skip: int = 0,
    limit: int = 10,
    current_user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    videos = await Video.get_all(db, skip=skip, limit=limit, user_id=current_user_id)
    
    # Get channel names for all videos
    from .database import Channel
    channel_ids = [v.channel_id for v in videos if v.channel_id]
    channels = {}
    if channel_ids:
        for cid in set(channel_ids):
            try:
                channel = await Channel.get_by_id(db, str(cid))
                if channel:
                    channels[str(cid)] = channel.name
            except:
                pass
    
    return [
        VideoResponse(
            id=str(v.id),
            title=v.title,
            description=v.description,
            duration=parse_duration(v.duration),
            resolution=v.resolution,
            bitrate=v.bitrate,
            file_size=v.file_size,
            status=v.status,
            hls_playlist_url=get_playlist_url(v.hls_playlist_url),
            thumbnail_url=get_thumbnail_url(v.thumbnail_url),
            is_private=v.is_private,
            tags=v.tags or [],
            created_at=v.created_at,
            user_id=str(v.user_id),
            channel_id=str(v.channel_id) if v.channel_id else None,
            views_count=v.views_count or 0,
            owner_username=channels.get(str(v.channel_id), "Неизвестный") if v.channel_id else "Неизвестный"
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

    # Get channel name for single video
    owner_name = None
    if video.channel_id:
        try:
            from .database import Channel
            channel = await Channel.get_by_id(db, str(video.channel_id))
            if channel:
                owner_name = channel.name
        except:
            pass
    
    return VideoResponse(
        id=str(video.id),
        title=video.title,
        description=video.description,
        duration=parse_duration(video.duration),
        resolution=video.resolution,
        bitrate=video.bitrate,
        file_size=video.file_size,
        status=video.status,
        hls_playlist_url=video.hls_playlist_url,
        thumbnail_url=get_thumbnail_url(video.thumbnail_url),
        is_private=video.is_private,
        tags=video.tags or [],
        created_at=video.created_at,
        user_id=str(video.user_id),
        owner_username=owner_name,
        channel_id=str(video.channel_id) if video.channel_id else None,
        views_count=video.views_count or 0
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
            expires=timedelta(seconds=settings.signed_url_expiry_seconds)
        )
        return {"signed_url": signed_url}
    except S3Error as e:
        logger.error(f"MinIO signed URL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate signed URL")

@app.get("/videos/{video_id}/thumbnail")
async def get_video_thumbnail(
    video_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get thumbnail URL for video"""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check permissions for private videos
    if video.is_private and (not user_id or str(video.user_id) != user_id):
        if not await check_private_video_permission(user_id, video.user_id):
            raise HTTPException(status_code=403, detail="Access denied")

    if not video.thumbnail_url:
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    # Return direct URL to MinIO (bucket is now public)
    try:
        thumbnail_url = f"http://localhost:9000/{settings.minio_bucket}/{video_id}/thumbnail.jpg"
        return {"thumbnail_url": thumbnail_url}
    except Exception as e:
        logger.error(f"Failed to generate thumbnail URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate thumbnail URL")

@app.get("/videos/{video_id}/playlist")
async def get_video_playlist(
    video_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get signed HLS playlist URL for video"""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check permissions for private videos
    if video.is_private and (not user_id or str(video.user_id) != user_id):
        if not await check_private_video_permission(user_id, video.user_id):
            raise HTTPException(status_code=403, detail="Access denied")

    if not video.hls_playlist_url:
        raise HTTPException(status_code=404, detail="Video not ready for streaming")

    # Return direct URL to MinIO (bucket is now public)
    try:
        playlist_url = f"http://localhost:9000/{settings.minio_bucket}/{video_id}/hls/master.m3u8"
        return {"playlist_url": playlist_url, "status": video.status}
    except Exception as e:
        logger.error(f"Failed to generate playlist URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate playlist URL")

@app.put("/videos/{video_id}")
async def update_video(
    video_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    is_private: Optional[bool] = None,
    tags: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")

    update_data = {}
    if title is not None:
        update_data['title'] = title
    if description is not None:
        update_data['description'] = description
    if is_private is not None:
        update_data['is_private'] = is_private
    if tags is not None:
        import json
        update_data['tags'] = json.loads(tags) if tags else []

    if update_data:
        await Video.update_metadata(db, video_id, **update_data)

    return {"message": "Video updated successfully"}

@app.delete("/videos/{video_id}")
async def delete_video(
    video_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")

    # Delete from MinIO
    try:
        # Delete original video
        minio_client.remove_object(settings.minio_bucket, video.minio_key)
        
        # Delete HLS files
        try:
            objects = minio_client.list_objects(settings.minio_bucket, prefix=f"{video_id}/hls/", recursive=True)
            for obj in objects:
                minio_client.remove_object(settings.minio_bucket, obj.object_name)
        except S3Error:
            pass  # HLS files might not exist
        
        # Delete thumbnail
        try:
            minio_client.remove_object(settings.minio_bucket, f"{video_id}/thumbnail.jpg")
        except S3Error:
            pass

        # Delete from database
        await db.execute(
            text("DELETE FROM videos WHERE id = :id"),
            {"id": video_id}
        )
        await db.commit()

        return {"message": "Video deleted successfully"}
    except S3Error as e:
        logger.error(f"MinIO delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete video")

@app.post("/videos/{video_id}/views")
async def record_view(
    video_id: str,
    watched_duration: Optional[int] = None,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Record view
    await db.execute(
        text("""
            INSERT INTO video_views (id, video_id, user_id, watched_duration, viewed_at)
            VALUES (gen_random_uuid(), :video_id, :user_id, :watched_duration, NOW())
        """),
        {
            "video_id": video_id,
            "user_id": user_id,
            "watched_duration": f"{watched_duration}s" if watched_duration else None,
        }
    )
    
    # Increment views count
    await db.execute(
        text("""
            UPDATE videos 
            SET views_count = views_count + 1 
            WHERE id = :video_id
        """),
        {"video_id": video_id}
    )
    await db.commit()

    return {"message": "View recorded"}

# Likes endpoints
@app.post("/videos/{video_id}/like")
async def like_video(
    video_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Like a video"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if already liked
    result = await db.execute(
        text("SELECT id FROM video_likes WHERE video_id = :video_id AND user_id = :user_id"),
        {"video_id": video_id, "user_id": user_id}
    )
    if result.first():
        return {"message": "Already liked", "likes_count": await get_likes_count(db, video_id)}
    
    # Add like
    await db.execute(
        text("INSERT INTO video_likes (id, video_id, user_id, created_at) VALUES (gen_random_uuid(), :video_id, :user_id, NOW())"),
        {"video_id": video_id, "user_id": user_id}
    )
    await db.commit()
    
    return {"message": "Liked", "likes_count": await get_likes_count(db, video_id)}

@app.delete("/videos/{video_id}/like")
async def unlike_video(
    video_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Remove like from video"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    await db.execute(
        text("DELETE FROM video_likes WHERE video_id = :video_id AND user_id = :user_id"),
        {"video_id": video_id, "user_id": user_id}
    )
    await db.commit()
    
    return {"message": "Unliked", "likes_count": await get_likes_count(db, video_id)}

@app.get("/videos/{video_id}/likes")
async def get_video_likes(
    video_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get likes count and check if user liked"""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    likes_count = await get_likes_count(db, video_id)
    
    user_liked = False
    if user_id:
        result = await db.execute(
            text("SELECT id FROM video_likes WHERE video_id = :video_id AND user_id = :user_id"),
            {"video_id": video_id, "user_id": user_id}
        )
        user_liked = result.first() is not None
    
    return {"likes_count": likes_count, "user_liked": user_liked}

async def get_likes_count(db: AsyncSession, video_id: str) -> int:
    """Get total likes count for video"""
    result = await db.execute(
        text("SELECT COUNT(*) FROM video_likes WHERE video_id = :video_id"),
        {"video_id": video_id}
    )
    return result.scalar() or 0

@app.post("/videos/{video_id}/views")
async def record_view(
    video_id: str,
    watched_duration: Optional[int] = None,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Record view
    await db.execute(
        text("""
            INSERT INTO video_views (id, video_id, user_id, watched_duration, viewed_at)
            VALUES (:id, :video_id, :user_id, :watched_duration, :viewed_at)
        """),
        {
            "id": str(uuid.uuid4()),
            "video_id": video_id,
            "user_id": user_id,
            "watched_duration": f"{watched_duration}s" if watched_duration else None,
            "viewed_at": datetime.utcnow()
        }
    )
    await db.commit()

    return {"message": "View recorded"}

# Channel endpoints
@app.post("/channels", response_model=ChannelResponse)
async def create_channel(
    channel_data: ChannelCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"POST /channels - user_id from token: {user_id} (type: {type(user_id)})")
    
    # Check if user already has a channel
    existing_channel = await Channel.get_by_owner(db, user_id)
    logger.info(f"Existing channel check: {existing_channel}")
    if existing_channel:
        logger.warning(f"User {user_id} already has channel: {existing_channel.id}")
        raise HTTPException(status_code=400, detail="User already has a channel")
    
    # Check if handle is already taken
    existing_handle = await Channel.get_by_handle(db, channel_data.handle)
    if existing_handle:
        raise HTTPException(status_code=400, detail="Handle already taken")
    
    logger.info(f"Creating channel with owner_id: {user_id}")
    channel = await Channel.create(db, **{
        "name": channel_data.name,
        "description": channel_data.description,
        "handle": channel_data.handle,
        "avatar_url": channel_data.avatar_url,
        "banner_url": channel_data.banner_url,
        "owner_id": user_id
    })
    logger.info(f"Channel created: id={channel.id}, owner_id={channel.owner_id}")
    
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        description=channel.description,
        handle=channel.handle,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        owner_id=str(channel.owner_id),
        subscribers_count=channel.subscribers_count,
        is_verified=channel.is_verified,
        created_at=channel.created_at
    )

# NOTE: /channels/my must be BEFORE /channels/{channel_id} to avoid routing conflicts
@app.get("/channels/my", response_model=ChannelResponse)
async def get_my_channel(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"GET /channels/my - user_id from token: {user_id} (type: {type(user_id)})")
    channel = await Channel.get_by_owner(db, user_id)
    logger.info(f"Channel lookup result: {channel}")
    if not channel:
        logger.warning(f"Channel not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        description=channel.description,
        handle=channel.handle,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        owner_id=str(channel.owner_id),
        subscribers_count=channel.subscribers_count,
        is_verified=channel.is_verified,
        created_at=channel.created_at
    )

@app.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db)
):
    channel = await Channel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        description=channel.description,
        handle=channel.handle,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        owner_id=str(channel.owner_id),
        subscribers_count=channel.subscribers_count,
        is_verified=channel.is_verified,
        created_at=channel.created_at
    )

@app.get("/channels/handle/{handle}", response_model=ChannelResponse)
async def get_channel_by_handle(
    handle: str,
    db: AsyncSession = Depends(get_db)
):
    channel = await Channel.get_by_handle(db, handle)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        description=channel.description,
        handle=channel.handle,
        avatar_url=channel.avatar_url,
        banner_url=channel.banner_url,
        owner_id=str(channel.owner_id),
        subscribers_count=channel.subscribers_count,
        is_verified=channel.is_verified,
        created_at=channel.created_at
    )

@app.get("/channels/{channel_id}/videos", response_model=List[VideoResponse])
async def get_channel_videos(
    channel_id: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    # Get channel info for owner_username
    channel = await Channel.get_by_id(db, channel_id)
    channel_name = channel.name if channel else "Неизвестный"
    
    videos = await Video.get_all(db, skip=skip, limit=limit, channel_id=channel_id)
    return [
        VideoResponse(
            id=str(v.id),
            title=v.title,
            description=v.description,
            duration=parse_duration(v.duration),
            resolution=v.resolution,
            bitrate=v.bitrate,
            file_size=v.file_size,
            status=v.status,
            hls_playlist_url=v.hls_playlist_url,
            thumbnail_url=get_thumbnail_url(v.thumbnail_url),
            is_private=v.is_private,
            tags=v.tags or [],
            created_at=v.created_at,
            user_id=str(v.user_id),
            channel_id=str(v.channel_id) if v.channel_id else None,
            views_count=v.views_count or 0,
            owner_username=channel_name
        ) for v in videos
    ]

# Subscription endpoints
@app.post("/channels/{channel_id}/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_channel(
    channel_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Check if channel exists
    channel = await Channel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if already subscribed
    if await Subscription.is_subscribed(db, user_id, channel_id):
        raise HTTPException(status_code=400, detail="Already subscribed")
    
    # Cannot subscribe to own channel
    if str(channel.owner_id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot subscribe to own channel")
    
    subscription = await Subscription.create(db, **{
        "subscriber_id": user_id,
        "channel_id": channel_id
    })
    
    return SubscriptionResponse(
        id=str(subscription.id),
        subscriber_id=str(subscription.subscriber_id),
        channel_id=str(subscription.channel_id),
        created_at=subscription.created_at
    )

@app.delete("/channels/{channel_id}/subscribe")
async def unsubscribe_from_channel(
    channel_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Check if channel exists
    channel = await Channel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if subscribed
    if not await Subscription.is_subscribed(db, user_id, channel_id):
        raise HTTPException(status_code=400, detail="Not subscribed")
    
    await Subscription.delete(db, user_id, channel_id)
    
    return {"message": "Unsubscribed successfully"}

@app.get("/channels/{channel_id}/is_subscribed")
async def check_subscription(
    channel_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    if not user_id:
        return {"is_subscribed": False}
    
    is_subscribed = await Subscription.is_subscribed(db, user_id, channel_id)
    return {"is_subscribed": is_subscribed}

@app.get("/subscriptions", response_model=List[ChannelResponse])
async def get_user_subscriptions(
    skip: int = 0,
    limit: int = 10,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    channels = await Subscription.get_user_subscriptions(db, user_id, skip=skip, limit=limit)
    return [
        ChannelResponse(
            id=str(c.id),
            name=c.name,
            description=c.description,
            handle=c.handle,
            avatar_url=c.avatar_url,
            banner_url=c.banner_url,
            owner_id=str(c.owner_id),
            subscribers_count=c.subscribers_count,
            is_verified=c.is_verified,
            created_at=c.created_at
        ) for c in channels
    ]

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
