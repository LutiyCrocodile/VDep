"""media routes."""
from fastapi import APIRouter

from ..storage import stream_media_object

router = APIRouter()


@router.get("/media/{object_path:path}")
async def serve_media(object_path: str):
    """Прокси объектов MinIO для HLS/превью (same-origin с API, без CORS)."""
    return await stream_media_object(object_path)
