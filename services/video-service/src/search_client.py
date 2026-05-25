"""Вызовы search-service (индексация / удаление из ES)."""
from __future__ import annotations

import logging

import httpx

from .config import settings
from .http_client import get_http_client

logger = logging.getLogger(__name__)


async def index_video_for_search(video_id: str) -> None:
    """Обновить документ в Elasticsearch (например, после нового просмотра)."""
    client = get_http_client()
    headers = {"Authorization": f"Bearer {settings.internal_auth_token}"}
    url = f"{settings.search_service_url.rstrip('/')}/internal/search/index/{video_id}"
    try:
        response = await client.post(url, headers=headers, timeout=15.0)
        if response.status_code not in (200, 201):
            logger.warning(
                "search index failed for %s: %s %s",
                video_id,
                response.status_code,
                response.text,
            )
    except httpx.RequestError as exc:
        logger.warning("search index error for %s: %s", video_id, exc)


async def deindex_video(video_id: str) -> None:
    """Убрать видео из Elasticsearch после удаления с канала."""
    client = get_http_client()
    headers = {"Authorization": f"Bearer {settings.internal_auth_token}"}
    url = f"{settings.search_service_url.rstrip('/')}/internal/search/index/{video_id}"
    try:
        response = await client.delete(url, headers=headers, timeout=15.0)
        if response.status_code not in (200, 404):
            logger.warning(
                "search deindex failed for %s: %s %s",
                video_id,
                response.status_code,
                response.text,
            )
        else:
            logger.info("Video %s removed from search index", video_id)
    except httpx.RequestError as exc:
        logger.warning("search deindex error for %s: %s", video_id, exc)
