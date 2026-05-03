import os
import subprocess
import json
import tempfile
import shutil
import uuid
from datetime import datetime
from minio import Minio
from minio.error import S3Error
from urllib.parse import urlparse
import logging
import pg8000
from .celery_app import celery_app
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sync database connection for Celery tasks
def get_db_connection():
    """Create sync database connection using pg8000"""
    parsed = urlparse(settings.database_url.replace('+asyncpg', ''))
    conn = pg8000.connect(
        user=parsed.username or 'user',
        password=parsed.password or 'password',
        host=parsed.hostname or 'db',
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/') or 'video_hosting'
    )
    return conn

def update_video_metadata(video_id, duration, resolution, bitrate, thumbnail_url):
    """Update video metadata in database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
                UPDATE videos
                SET duration = %s, resolution = %s, bitrate = %s, 
                    thumbnail_url = %s, updated_at = NOW()
                WHERE id = %s
            """,
            (duration, resolution, bitrate, thumbnail_url, video_id)
        )
        conn.commit()
    finally:
        conn.close()

def update_video_status(video_id, status, hls_url=None):
    """Update video status in database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if hls_url:
            cursor.execute(
                "UPDATE videos SET status = %s, hls_playlist_url = %s WHERE id = %s",
                (status, hls_url, video_id)
            )
        else:
            cursor.execute(
                "UPDATE videos SET status = %s WHERE id = %s",
                (status, video_id)
            )
        conn.commit()
    finally:
        conn.close()

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

            # Generate thumbnail
            thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
            thumbnail_minio_key = f"{video_id}/thumbnail.jpg"
            generate_thumbnail(local_video_path, thumbnail_path)
            minio_client.fput_object(settings.minio_bucket, thumbnail_minio_key, thumbnail_path)
            logger.info(f"Thumbnail uploaded to {thumbnail_minio_key}")

            # Update database with metadata
            update_video_metadata(
                video_id,
                metadata.get('duration'),
                metadata.get('resolution'),
                metadata.get('bitrate'),
                f"/{video_id}/thumbnail.jpg"
            )

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
                    "-vf", f"{get_scale_filter(quality)},drawtext=text='DGI':fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:x=(w-text_w)/2:y=h-text_h-10",
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

            # Generate HLS playlist URL (using nginx proxy to MinIO)
            hls_url = f"/videos/{video_id}/hls/master.m3u8"

            # Update database
            update_video_status(video_id, 'ready', hls_url)

            logger.info(f"Transcoding completed for video {video_id}")

            # Trigger subtitle generation
            self.app.send_task(
                "src.tasks.generate_subtitles",
                args=[video_id, minio_key],
                queue="video_processing"
            )

    except Exception as e:
        logger.error(f"Transcoding failed for video {video_id}: {str(e)}")
        # Update status to failed
        update_video_status(video_id, 'failed')
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
        "duration": int(float(duration)) if duration else None,
        "resolution": resolution,
        "bitrate": int(bitrate) if bitrate else None
    }

def generate_thumbnail(video_path: str, output_path: str, time: str = "00:00:01"):
    """Generate thumbnail from video at specified time"""
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-ss", time,  # Seek to time
        "-vframes", "1",  # Extract one frame
        "-vf", "scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2",
        "-y",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Thumbnail generation error: {result.stderr}")
        # Create a placeholder if generation fails
        subprocess.run([
            "ffmpeg",
            "-f", "lavfi",
            "-i", "color=c=black:s=320x180",
            "-frames:v", "1",
            "-y",
            output_path
        ], capture_output=True)
    return output_path

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
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                    INSERT INTO subtitles (id, video_id, language, content, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """,
                (str(uuid.uuid4()), video_id, "ru", "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nПлейсхолдер субтитров\n")
            )
            conn.commit()
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Subtitle generation failed for video {video_id}: {str(e)}")
        # Don't fail the task, just log the error
