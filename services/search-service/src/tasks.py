from elasticsearch import AsyncElasticsearch
from .celery_app import celery_app
from .config import settings
import logging
import httpx

logger = logging.getLogger(__name__)

@celery_app.task
def index_video_task(video_id: str):
    """
    Celery task to index a video in Elasticsearch
    """
    import asyncio
    
    async def _index():
        es_client = AsyncElasticsearch([settings.elasticsearch_hosts])
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.video_service_url}/videos/{video_id}",
                    headers={"Authorization": f"Bearer {settings.internal_auth_token}"}
                )
                if response.status_code != 200:
                    logger.error(f"Failed to fetch video {video_id}")
                    return
                
                video_data = response.json()
            
            doc = {
                "id": video_id,
                "title": video_data["title"],
                "description": video_data.get("description", ""),
                "tags": video_data.get("tags", []),
                "subtitles": "",
                "duration": video_data.get("duration"),
                "resolution": video_data.get("resolution"),
                "file_size": video_data["file_size"],
                "status": video_data["status"],
                "hls_playlist_url": video_data.get("hls_playlist_url"),
                "is_private": video_data["is_private"],
                "user_id": video_data["user_id"],
                "created_at": video_data["created_at"]
            }
            
            await es_client.index(index=settings.elasticsearch_index, id=video_id, document=doc)
            await es_client.indices.refresh(index=settings.elasticsearch_index)
            
            logger.info(f"Video {video_id} indexed successfully")
        except Exception as e:
            logger.error(f"Failed to index video {video_id}: {e}")
        finally:
            await es_client.close()
    
    asyncio.run(_index())
