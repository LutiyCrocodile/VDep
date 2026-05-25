"""Публичные URL объектов MinIO (превью через video-service /media)."""
from __future__ import annotations

from .config import settings


def stream_thumbnail_minio_key(stream_id: str) -> str:
    return f"streams/{stream_id}/thumbnail.jpg"


def stream_thumbnail_db_path(stream_id: str) -> str:
    return f"/streams/{stream_id}/thumbnail.jpg"


def get_public_thumbnail_url(
    thumbnail_path: str | None,
    stream_id: str | None = None,
    *,
    allow_default: bool = False,
) -> str | None:
    raw = (thumbnail_path or "").strip()
    if not raw and stream_id and allow_default:
        raw = stream_thumbnail_db_path(stream_id)
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    key = raw.lstrip("/")
    if not key.startswith("media/"):
        key = f"media/{key}"
    return f"{settings.public_video_api_url.rstrip('/')}/{key}"
