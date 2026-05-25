import logging
import os

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from minio.error import S3Error

from .config import settings
from .deps import minio_client

logger = logging.getLogger(__name__)

_MEDIA_TYPES = {
    ".m3u8": "application/vnd.apple.mpegurl",
    ".ts": "video/mp2t",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _minio_public_base_url() -> str:
    ep = (settings.minio_external_endpoint or "").strip()
    if not ep:
        ep = "localhost:9000"
    if ep.startswith("http://") or ep.startswith("https://"):
        return ep.rstrip("/")
    scheme = "https" if settings.minio_secure else "http"
    return f"{scheme}://{ep}".rstrip("/")


def _normalize_object_key(object_path: str) -> str:
    if not object_path:
        return ""
    bucket = settings.minio_bucket
    key = object_path.lstrip("/")
    if key.startswith(f"{bucket}/"):
        key = key[len(bucket) + 1 :]
    return key


def _storage_public_url(object_path: str) -> str:
    if not object_path:
        return ""
    if object_path.startswith("http"):
        return object_path
    key = _normalize_object_key(object_path)
    if settings.public_media_via_api:
        return f"{settings.public_video_api_url.rstrip('/')}/media/{key}"
    base = _minio_public_base_url()
    bucket = settings.minio_bucket
    return f"{base}/{bucket}/{key}"


def get_thumbnail_url(thumbnail_path: str) -> str:
    return _storage_public_url(thumbnail_path)


def get_playlist_url(playlist_path: str) -> str:
    return _storage_public_url(playlist_path)


async def stream_media_object(object_path: str) -> StreamingResponse:
    key = _normalize_object_key(object_path)
    if not key:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        obj = minio_client.get_object(settings.minio_bucket, key)
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchBucket"):
            raise HTTPException(status_code=404, detail="Not found")
        logger.error("MinIO get_object %s: %s", key, e)
        raise HTTPException(status_code=500, detail="Storage error")

    ext = os.path.splitext(key)[1].lower()
    media_type = _MEDIA_TYPES.get(ext, "application/octet-stream")

    def stream():
        try:
            for chunk in obj.stream(32 * 1024):
                yield chunk
        finally:
            obj.close()
            obj.release_conn()

    return StreamingResponse(
        stream(),
        media_type=media_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=120",
        },
    )
