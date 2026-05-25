"""videos routes."""
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
from ..search_client import deindex_video
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
from ..thumbnail_processing import (
    ALLOWED_CONTENT_TYPES,
    MAX_THUMBNAIL_BYTES,
    process_custom_thumbnail,
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/videos/upload/init", response_model=VideoUploadResponse)
async def init_upload(
    title: str = Form(...),
    description: str = Form(""),
    is_private: bool = Form(False),
    tags: str = Form(""),  # JSON array as string
    classification: str = Form("public"),  # public, internal, confidential, restricted
    filename: str = Form(...),
    file_size: int = Form(...),
    channel_id: Optional[str] = Form(None),
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"[Upload Init] Classification received: {classification}")

    # Validate classification level
    valid_classifications = ['public', 'internal', 'confidential', 'restricted']
    if classification not in valid_classifications:
        raise HTTPException(status_code=400, detail=f"Invalid classification. Must be one of: {', '.join(valid_classifications)}")

    # Resolve channel: use provided channel_id or look up user's channel
    resolved_channel_id = channel_id
    if not resolved_channel_id:
        channel = await Channel.get_by_owner(db, user_id)
        if channel:
            resolved_channel_id = str(channel.id)

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
        "channel_id": resolved_channel_id,
        "file_size": file_size,
        "minio_key": minio_key,
        "status": "uploading",
        "is_private": is_private,
        "tags": tags_list,
        "classification": classification
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

@router.post("/videos/{video_id}/upload-data")
async def upload_video_data(
    video_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(require_current_user),
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

@router.post("/videos/{video_id}/complete")
async def complete_upload(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify video ownership
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")

    # Update status to uploaded (but don't start transcoding yet)
    await Video.update_status(db, video_id, "uploaded")

    return {"message": "Upload completed, ready to publish", "status": "uploaded", "video_id": video_id}


def _assert_owner_can_edit_thumbnail(video: Video, user_id: str) -> None:
    if str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != "uploaded":
        raise HTTPException(
            status_code=400,
            detail="Превью можно изменить только до публикации видео",
        )


@router.post("/videos/{video_id}/thumbnail")
async def upload_video_thumbnail(
    video_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить пользовательское превью (до publish)."""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    _assert_owner_can_edit_thumbnail(video, user_id)

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Допустимые форматы: JPEG, PNG, WebP",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Пустой файл")
    if len(raw) > MAX_THUMBNAIL_BYTES:
        raise HTTPException(status_code=413, detail="Максимальный размер превью: 5 МБ")

    try:
        jpeg_bytes = process_custom_thumbnail(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    thumbnail_minio_key = f"{video_id}/thumbnail.jpg"
    thumbnail_db_path = f"/{video_id}/thumbnail.jpg"

    try:
        minio_client.put_object(
            settings.minio_bucket,
            thumbnail_minio_key,
            io.BytesIO(jpeg_bytes),
            len(jpeg_bytes),
            content_type="image/jpeg",
        )
        await Video.update_metadata(db, video_id, thumbnail_url=thumbnail_db_path)
    except S3Error as e:
        logger.error(f"MinIO thumbnail upload error: {e}")
        raise HTTPException(status_code=500, detail="Не удалось сохранить превью") from e

    return {
        "message": "Thumbnail uploaded",
        "thumbnail_url": get_thumbnail_url(thumbnail_db_path),
    }


@router.delete("/videos/{video_id}/thumbnail")
async def delete_video_thumbnail(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить пользовательское превью (до publish)."""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    _assert_owner_can_edit_thumbnail(video, user_id)

    if not video.thumbnail_url:
        return {"message": "No custom thumbnail"}

    try:
        minio_client.remove_object(settings.minio_bucket, f"{video_id}/thumbnail.jpg")
    except S3Error as e:
        logger.warning(f"MinIO thumbnail delete: {e}")

    await Video.update_metadata(db, video_id, thumbnail_url=None)
    return {"message": "Thumbnail removed"}


@router.post("/videos/{video_id}/publish")
async def publish_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish video - starts transcoding process"""
    # Verify video ownership
    video = await Video.get_by_id(db, video_id)
    if not video or str(video.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Video not found")

    logger.info(f"[Publish] Video {video_id} classification: {video.classification}")

    # Check if video is in uploaded status
    if video.status != 'uploaded':
        raise HTTPException(status_code=400, detail=f"Cannot publish video with status: {video.status}. Only 'uploaded' videos can be published.")

    # Start transcoding in background
    background_tasks.add_task(start_transcoding, video_id, video.minio_key)

    return {"message": "Publishing started", "status": "transcoding", "video_id": video_id}

@router.get("/videos", response_model=List[VideoResponse])
async def list_videos(
    skip: int = 0,
    limit: int = 10,
    current_user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get user's classification level
    user_level = await get_user_classification_level(current_user_id)

    videos = await Video.get_all(db, skip=skip, limit=limit, user_id=current_user_id)

    from ..database import VideoUserAccess

    owner_restricted_ids = [
        str(v.id)
        for v in videos
        if str(v.user_id) == current_user_id and v.classification == "restricted"
    ]
    other_restricted_ids = [
        str(v.id)
        for v in videos
        if str(v.user_id) != current_user_id and v.classification == "restricted"
    ]
    share_counts = await VideoUserAccess.get_share_counts(db, owner_restricted_ids)
    access_ids = await VideoUserAccess.get_access_video_ids_for_user(
        db, other_restricted_ids, current_user_id
    )

    final_videos = []
    for v in videos:
        vid = str(v.id)
        if str(v.user_id) == current_user_id:
            if v.classification == "restricted":
                if share_counts.get(vid, 0) == 0:
                    final_videos.append(v)
            else:
                final_videos.append(v)
        elif v.classification == "restricted":
            if vid in access_ids:
                final_videos.append(v)
        elif can_access_classification(user_level, v.classification or "public"):
            final_videos.append(v)

    channel_id_list = [str(v.channel_id) for v in final_videos if v.channel_id]
    channels_map = await Channel.get_by_ids(db, channel_id_list)

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
            owner_username=channels_map[str(v.channel_id)].name
            if v.channel_id and str(v.channel_id) in channels_map
            else "Неизвестный",
            channel_handle=channels_map[str(v.channel_id)].handle
            if v.channel_id and str(v.channel_id) in channels_map
            else None,
            transcoding_progress=v.transcoding_progress or 0,
            classification=v.classification or 'public',
        )
        for v in final_videos
    ]

@router.get("/videos/liked")
async def get_liked_videos(
    skip: int = 0,
    limit: int = 20,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get videos liked by current user"""
    result = await db.execute(
        text("""
            SELECT v.*, c.name as channel_name, c.handle as channel_handle FROM videos v
            INNER JOIN video_likes vl ON v.id = vl.video_id
            LEFT JOIN channels c ON v.channel_id = c.id
            WHERE vl.user_id = :user_id
            AND v.status = 'ready'
            ORDER BY vl.created_at DESC
            LIMIT :limit OFFSET :skip
        """),
        {"user_id": user_id, "limit": limit, "skip": skip}
    )
    rows = result.fetchall()
    
    videos = []
    for row in rows:
        video_dict = {
            "id": str(row.id),
            "title": row.title,
            "description": row.description,
            "thumbnail_url": get_thumbnail_url(row.thumbnail_url),
            "duration": row.duration.total_seconds() if row.duration else None,
            "views_count": row.views_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "user_id": str(row.user_id),
            "channel_id": str(row.channel_id) if row.channel_id else None,
            "owner_username": row.channel_name if row.channel_name else None,
            "channel_handle": row.channel_handle if row.channel_handle else None,
            "status": row.status,
            "classification": row.classification,
        }
        videos.append(video_dict)
    
    return {"videos": videos, "total": len(videos)}

@router.get("/videos/history")
async def get_view_history(
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """Get user's view history with duplicates (each view is recorded)"""
    query = """
        SELECT 
            v.*,
            vv.viewed_at,
            vv.watched_duration,
            c.name as channel_name,
            c.handle as channel_handle
        FROM video_views vv
        JOIN videos v ON vv.video_id = v.id
        LEFT JOIN channels c ON v.channel_id = c.id
        WHERE vv.user_id = :user_id
        ORDER BY vv.viewed_at DESC
        LIMIT :limit OFFSET :skip
    """
    result = await db.execute(text(query), {"user_id": user_id, "limit": limit, "skip": skip})
    rows = result.fetchall()
    
    history = []
    for row in rows:
        video_dict = {
            "id": str(row.id),
            "title": row.title,
            "description": row.description,
            "thumbnail_url": get_thumbnail_url(row.thumbnail_url),
            "duration": parse_duration(row.duration),
            "views_count": row.views_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "user_id": str(row.user_id),
            "channel_id": str(row.channel_id) if row.channel_id else None,
            "owner_username": row.channel_name if row.channel_name else None,
            "channel_handle": row.channel_handle if row.channel_handle else None,
            "status": row.status,
            "classification": row.classification,
            "viewed_at": row.viewed_at.isoformat() if row.viewed_at else None,
            "watched_duration": row.watched_duration,
        }
        history.append(video_dict)
    
    return {"history": history}

@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    user_id: str = Depends(require_current_user),
    range_header: str = Header(None, alias="range"),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Type narrowing for linter
    assert video is not None

    await enforce_video_view_access(db, video, user_id)

    # Get channel name and handle for single video
    owner_name = None
    channel_handle = None
    if video.channel_id:
        try:
            from ..database import Channel
            channel = await Channel.get_by_id(db, str(video.channel_id))
            if channel:
                owner_name = channel.name
                channel_handle = channel.handle
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
        hls_playlist_url=get_playlist_url(video.hls_playlist_url or ""),
        thumbnail_url=get_thumbnail_url(video.thumbnail_url),
        is_private=video.is_private,
        tags=video.tags or [],
        created_at=video.created_at,
        user_id=str(video.user_id),
        owner_username=owner_name,
        channel_handle=channel_handle,
        channel_id=str(video.channel_id) if video.channel_id else None,
        views_count=video.views_count or 0,
        transcoding_progress=video.transcoding_progress or 0,
        classification=video.classification or 'public'
    )


@router.get("/videos/{video_id}/signed-url")
async def get_signed_url(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    await enforce_video_view_access(db, video, user_id)

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

@router.get("/videos/{video_id}/thumbnail")
async def get_video_thumbnail(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get thumbnail URL for video"""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    await enforce_video_view_access(db, video, user_id)

    if not video.thumbnail_url:
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    # Return direct URL to MinIO (bucket is now public)
    try:
        thumbnail_url = get_thumbnail_url(video.thumbnail_url or f"/{video_id}/thumbnail.jpg")
        return {"thumbnail_url": thumbnail_url}
    except Exception as e:
        logger.error(f"Failed to generate thumbnail URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate thumbnail URL")

@router.get("/videos/{video_id}/playlist")
async def get_video_playlist(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get signed HLS playlist URL for video"""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    await enforce_video_view_access(db, video, user_id)

    if not video.hls_playlist_url:
        raise HTTPException(status_code=404, detail="Video not ready for streaming")

    try:
        playlist_url = get_playlist_url(video.hls_playlist_url or f"{video_id}/hls/master.m3u8")
        return {"playlist_url": playlist_url, "status": video.status}
    except Exception as e:
        logger.error(f"Failed to generate playlist URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate playlist URL")

@router.put("/videos/{video_id}")
async def update_video(
    video_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    is_private: Optional[bool] = None,
    tags: Optional[str] = None,
    user_id: str = Depends(require_current_user),
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

@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: str,
    user_id: str = Depends(require_current_user),
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

        await deindex_video(video_id)

        return {"message": "Video deleted successfully"}
    except S3Error as e:
        logger.error(f"MinIO delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete video")

@router.post("/videos/{video_id}/views")
async def record_view(
    video_id: str,
    request: ViewRecordRequest,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check if user/session already viewed this video
    existing_view = None
    if user_id:
        # Authenticated user - check by user_id
        existing_view = await db.execute(
            text("""
                SELECT id FROM video_views 
                WHERE video_id = :video_id AND user_id = :user_id
                LIMIT 1
            """),
            {"video_id": video_id, "user_id": user_id}
        )
    elif request.session_id:
        # Anonymous user - check by session_id
        existing_view = await db.execute(
            text("""
                SELECT id FROM video_views 
                WHERE video_id = :video_id AND session_id = :session_id
                LIMIT 1
            """),
            {"video_id": video_id, "session_id": request.session_id}
        )
    
    if existing_view and existing_view.first():
        # Already viewed - update watch duration and timestamp
        if user_id:
            await db.execute(
                text("""
                    UPDATE video_views 
                    SET watched_duration = :watched_duration, viewed_at = NOW()
                    WHERE video_id = :video_id AND user_id = :user_id
                """),
                {
                    "video_id": video_id,
                    "user_id": user_id,
                    "watched_duration": f"{request.watched_duration}s" if request.watched_duration else None,
                }
            )
        else:
            await db.execute(
                text("""
                    UPDATE video_views 
                    SET watched_duration = :watched_duration, viewed_at = NOW()
                    WHERE video_id = :video_id AND session_id = :session_id
                """),
                {
                    "video_id": video_id,
                    "session_id": request.session_id,
                    "watched_duration": f"{request.watched_duration}s" if request.watched_duration else None,
                }
            )
        await db.commit()
        return {"message": "View already recorded", "already_viewed": True}

    # Record new view
    await db.execute(
        text("""
            INSERT INTO video_views (id, video_id, user_id, session_id, watched_duration, viewed_at)
            VALUES (gen_random_uuid(), :video_id, :user_id, :session_id, :watched_duration, NOW())
        """),
        {
            "video_id": video_id,
            "user_id": user_id,
            "session_id": request.session_id if not user_id else None,
            "watched_duration": f"{request.watched_duration}s" if request.watched_duration else None,
        }
    )

    # Increment views count only for new views
    await db.execute(
        text("""
            UPDATE videos 
            SET views_count = views_count + 1 
            WHERE id = :video_id
        """),
        {"video_id": video_id}
    )
    await db.commit()

    return {"message": "View recorded", "already_viewed": False}

# Likes endpoints
@router.post("/videos/{video_id}/like")
async def like_video(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Like a video"""
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

@router.delete("/videos/{video_id}/like")
async def unlike_video(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove like from video"""
    await db.execute(
        text("DELETE FROM video_likes WHERE video_id = :video_id AND user_id = :user_id"),
        {"video_id": video_id, "user_id": user_id}
    )
    await db.commit()
    
    return {"message": "Unliked", "likes_count": await get_likes_count(db, video_id)}

@router.get("/videos/{video_id}/likes")
async def get_video_likes(
    video_id: str,
    user_id: str = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get likes count and check if user liked"""
    video = await Video.get_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    likes_count = await get_likes_count(db, video_id)
    
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

