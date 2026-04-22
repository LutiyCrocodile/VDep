import os
import subprocess
import json
import tempfile
import shutil
from minio import Minio
from minio.error import S3Error
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse
import logging
from .celery_app import celery_app
from .database import Video
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup for Celery tasks (synchronous)
engine = create_engine(settings.database_url.replace('+asyncpg', ''), echo=False, future=True)
sync_session = sessionmaker(engine, expire_on_commit=False)

# MinIO client
minio_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure
)

@celery_app.task(bind=True)
def transcode_video(self, video_id: str, minio_key: str):
    """
    Transcode video to multiple HLS qualities
    """
    logger.info(f"Starting transcoding for video {video_id}")

    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video from MinIO
            local_video_path = os.path.join(temp_dir, "original.mp4")
            minio_client.fget_object(settings.minio_bucket, minio_key, local_video_path)

            # Get video metadata
            metadata = get_video_metadata(local_video_path)
            logger.info(f"Video metadata: {metadata}")

            # Update database with metadata
            with sync_session() as db:
                db.execute(
                    text("""
                        UPDATE videos
                        SET duration = :duration, resolution = :resolution, bitrate = :bitrate, updated_at = NOW()
                        WHERE id = :video_id
                    """),
                    {
                        "video_id": video_id,
                        "duration": metadata.get('duration'),
                        "resolution": metadata.get('resolution'),
                        "bitrate": metadata.get('bitrate')
                    }
                )
                db.commit()

            # Create HLS directory
            hls_dir = os.path.join(temp_dir, "hls")
            os.makedirs(hls_dir)

            # Transcode to multiple qualities
            master_playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
            qualities = settings.transcoding_qualities

            for quality in qualities:
                logger.info(f"Transcoding to {quality}")
                quality_dir = os.path.join(hls_dir, quality)
                os.makedirs(quality_dir)

                # Generate HLS playlist for this quality
                playlist_path = os.path.join(quality_dir, "playlist.m3u8")
                segment_pattern = os.path.join(quality_dir, "segment_%03d.ts")

                # FFmpeg command for transcoding
                cmd = [
                    "ffmpeg",
                    "-i", local_video_path,
                    "-vf", f"scale={get_scale_filter(quality)},drawtext=text='DGI':fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:x=(w-text_w)/2:y=h-text_h-10",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-ac", "2",
                    "-ar", "44100",
                    "-f", "hls",
                    "-hls_time", str(settings.hls_segment_duration),
                    "-hls_playlist_type", "vod",
                    "-hls_segment_filename", segment_pattern,
                    "-y",
                    playlist_path
                ]

                # Add quality-specific bitrate
                bitrate = get_bitrate_for_quality(quality)
                cmd.insert(-1, "-b:v")
                cmd.insert(-1, bitrate)

                result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
                if result.returncode != 0:
                    logger.error(f"FFmpeg error for {quality}: {result.stderr}")
                    raise Exception(f"Transcoding failed for {quality}")

                # Upload HLS files to MinIO
                hls_minio_key = f"{video_id}/hls/{quality}/"
                upload_directory_to_minio(quality_dir, hls_minio_key)

                # Add to master playlist
                bandwidth = get_bandwidth_for_quality(quality)
                master_playlist_content += f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={get_resolution_for_quality(quality)}\n'
                master_playlist_content += f'{quality}/playlist.m3u8\n'

            # Upload master playlist
            master_playlist_path = os.path.join(hls_dir, "master.m3u8")
            with open(master_playlist_path, 'w') as f:
                f.write(master_playlist_content)

            master_minio_key = f"{video_id}/hls/master.m3u8"
            minio_client.fput_object(settings.minio_bucket, master_minio_key, master_playlist_path)

            # Generate HLS playlist URL (using Nginx VOD module)
            hls_url = f"/vod/{video_id}/master.m3u8"

            # Update database
            with sync_session() as db:
                db.execute(
                    text("""
                        UPDATE videos
                        SET hls_playlist_url = :hls_url, status = :status, updated_at = NOW()
                        WHERE id = :video_id
                    """),
                    {
                        "video_id": video_id,
                        "hls_url": hls_url,
                        "status": "ready"
                    }
                )
                db.commit()

            logger.info(f"Transcoding completed for video {video_id}")

            # Trigger subtitle generation
            self.app.send_task(
                "video_service.tasks.generate_subtitles",
                args=[video_id, minio_key],
                queue="video_processing"
            )

    except Exception as e:
        logger.error(f"Transcoding failed for video {video_id}: {str(e)}")
        # Update status to failed
        async with async_session() as db:
            await Video.update_status(db, video_id, "failed")
        raise

def get_video_metadata(video_path: str) -> dict:
    """Extract video metadata using ffprobe"""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)

    # Extract duration, resolution, bitrate
    format_info = data.get("format", {})
    duration = format_info.get("duration")

    # Find video stream
    video_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    resolution = None
    bitrate = None
    if video_stream:
        width = video_stream.get("width")
        height = video_stream.get("height")
        if width and height:
            resolution = f"{width}x{height}"
        bitrate = video_stream.get("bit_rate")

    return {
        "duration": f"{duration}s" if duration else None,
        "resolution": resolution,
        "bitrate": int(bitrate) if bitrate else None
    }

def get_scale_filter(quality: str) -> str:
    """Get FFmpeg scale filter for quality"""
    scales = {
        "180p": "320:180",
        "360p": "640:360",
        "480p": "854:480",
        "720p": "1280:720",
        "1080p": "1920:1080"
    }
    return f"scale={scales.get(quality, '640:360')}:force_original_aspect_ratio=decrease,pad={scales.get(quality, '640:360')}:(ow-iw)/2:(oh-ih)/2"

def get_bitrate_for_quality(quality: str) -> str:
    """Get bitrate for quality"""
    bitrates = {
        "180p": "500k",
        "360p": "1000k",
        "480p": "2500k",
        "720p": "5000k",
        "1080p": "8000k"
    }
    return bitrates.get(quality, "1000k")

def get_bandwidth_for_quality(quality: str) -> int:
    """Get bandwidth for quality (in bits per second)"""
    bandwidths = {
        "180p": 500000,
        "360p": 1000000,
        "480p": 2500000,
        "720p": 5000000,
        "1080p": 8000000
    }
    return bandwidths.get(quality, 1000000)

def get_resolution_for_quality(quality: str) -> str:
    """Get resolution for quality"""
    resolutions = {
        "180p": "320x180",
        "360p": "640x360",
        "480p": "854x480",
        "720p": "1280x720",
        "1080p": "1920x1080"
    }
    return resolutions.get(quality, "640x360")

def upload_directory_to_minio(local_dir: str, minio_prefix: str):
    """Upload directory contents to MinIO recursively"""
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            # Calculate relative path from local_dir
            rel_path = os.path.relpath(local_path, local_dir)
            minio_key = f"{minio_prefix}{rel_path}"

            try:
                minio_client.fput_object(settings.minio_bucket, minio_key, local_path)
                logger.info(f"Uploaded {minio_key}")
            except S3Error as e:
                logger.error(f"Failed to upload {minio_key}: {e}")

@celery_app.task
def generate_subtitles(video_id: str, minio_key: str):
    """
    Generate subtitles using Vosk speech recognition
    """
    logger.info(f"Starting subtitle generation for video {video_id}")

    try:
        # This is a placeholder for Vosk integration
        # In a real implementation, you would:
        # 1. Download video from MinIO
        # 2. Extract audio using FFmpeg
        # 3. Process audio with Vosk
        # 4. Generate WebVTT subtitles
        # 5. Save subtitles to database and MinIO

        # For now, we'll just log and mark as completed
        logger.info(f"Subtitle generation completed for video {video_id} (placeholder)")

        # Update search index with subtitles (placeholder)
        with sync_session() as db:
            # Placeholder: In real implementation, this would insert subtitle content
            db.execute(
                text("""
                    INSERT INTO subtitles (id, video_id, language, content, created_at)
                    VALUES (:id, :video_id, :language, :content, :created_at)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "video_id": video_id,
                    "language": "ru",
                    "content": "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nПлейсхолдер субтитров\n",
                    "created_at": datetime.utcnow()
                }
            )
            db.commit()

    except Exception as e:
        logger.error(f"Subtitle generation failed for video {video_id}: {str(e)}")
        # Don't fail the task, just log the error
