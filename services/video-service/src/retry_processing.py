#!/usr/bin/env python3
"""Retry video processing for uploaded videos"""
import asyncio
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

from src.database import async_session, Video
from src.tasks import transcode_video
from sqlalchemy import text

async def retry_uploaded_videos():
    async with async_session() as db:
        # Get all uploaded videos
        result = await db.execute(
            text("SELECT id, minio_key FROM videos WHERE status = 'uploaded'")
        )
        videos = result.fetchall()
        
        print(f"Found {len(videos)} videos to process")
        
        for video in videos:
            video_id = str(video.id)
            minio_key = video.minio_key
            print(f"Queueing video {video_id} for processing...")
            
            # Send to celery
            transcode_video.delay(video_id, minio_key)
        
        print("All videos queued for processing!")

if __name__ == "__main__":
    asyncio.run(retry_uploaded_videos())
