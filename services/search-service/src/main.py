from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
from pydantic import BaseModel
from typing import Optional, List
import httpx
import logging
from elasticsearch import AsyncElasticsearch

from .database import get_db, create_tables, Subtitle
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

es_client = AsyncElasticsearch([settings.elasticsearch_hosts])

class VideoSearchResult(BaseModel):
    id: str
    title: str
    description: Optional[str]
    duration: Optional[str]
    resolution: Optional[str]
    file_size: int
    status: str
    hls_playlist_url: Optional[str]
    is_private: bool
    tags: List[str]
    created_at: str
    user_id: str
    relevance_score: float
    highlights: Optional[dict] = None

class SubtitleResponse(BaseModel):
    id: str
    video_id: str
    language: str
    content: str
    created_at: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await es_client.ping()
    logger.info("Search service started")
    yield
    await es_client.close()
    logger.info("Search service shutting down")

app = FastAPI(title="Search Service", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
                raise HTTPException(status_code=401, detail="Invalid token")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")

@app.get("/search", response_model=List[VideoSearchResult])
async def search_videos(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    tags: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security, auto_error=False),
):
    """
    Search videos by title, description, tags, and subtitles
    Public videos are accessible without authentication
    """
    try:
        # Get user_id if authenticated
        user_id = None
        if credentials:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"{settings.auth_service_url}/users/me",
                        headers={"Authorization": f"Bearer {credentials.credentials}"}
                    )
                    if response.status_code == 200:
                        user_data = response.json()
                        user_id = user_data["id"]
                except httpx.RequestError:
                    pass  # Continue without user_id

        # Build query
        must_clauses = [
            {
                "multi_match": {
                    "query": q,
                    "fields": ["title^3", "description^2", "tags", "subtitles"],
                    "fuzziness": "AUTO"
                }
            }
        ]

        # Filter by tags if provided
        if tags:
            tag_list = tags.split(",")
            must_clauses.append({
                "terms": {
                    "tags": tag_list
                }
            })

        # Filter by access (public or user's own videos if authenticated)
        if user_id:
            must_clauses.append({
                "bool": {
                    "should": [
                        {"term": {"is_private": False}},
                        {"term": {"user_id": user_id}}
                    ]
                }
            })
        else:
            # Only public videos for unauthenticated users
            must_clauses.append({
                "term": {"is_private": False}
            })
        
        search_body = {
            "from": skip,
            "size": limit,
            "query": {
                "bool": {
                    "must": must_clauses
                }
            },
            "highlight": {
                "fields": {
                    "title": {},
                    "description": {},
                    "subtitles": {}
                }
            }
        }

        response = await es_client.search(index=settings.elasticsearch_index, body=search_body)
        
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            highlights = hit.get("highlight", {})
            
            results.append(VideoSearchResult(
                id=source["id"],
                title=source["title"],
                description=source.get("description"),
                duration=source.get("duration"),
                resolution=source.get("resolution"),
                file_size=source["file_size"],
                status=source["status"],
                hls_playlist_url=source.get("hls_playlist_url"),
                is_private=source["is_private"],
                tags=source.get("tags", []),
                created_at=source["created_at"],
                user_id=source["user_id"],
                relevance_score=hit["_score"],
                highlights=highlights
            ))
        
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/videos/{video_id}/subtitles", response_model=List[SubtitleResponse])
async def get_subtitles(
    video_id: str,
    language: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subtitles for a video
    """
    subtitles = await Subtitle.get_by_video_id(db, video_id)
    
    if language:
        subtitles = [s for s in subtitles if s.language == language]
    
    return [
        SubtitleResponse(
            id=str(s.id),
            video_id=str(s.video_id),
            language=s.language,
            content=s.content,
            created_at=str(s.created_at)
        ) for s in subtitles
    ]

@app.post("/search/index/{video_id}")
async def index_video(
    video_id: str,
    background_tasks: dict,
    user_id: str = Depends(get_current_user_id)
):
    """
    Index a video for search (triggered after transcoding)
    This endpoint is called by video-service after transcoding completes
    """
    try:
        # Fetch video data from video-service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.video_service_url}/videos/{video_id}",
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Video not found")
            
            video_data = response.json()
        
        # Fetch subtitles
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.video_service_url}/videos/{video_id}/subtitles",
                headers={"Authorization": f"Bearer {settings.internal_auth_token}"}
            )
            subtitles_content = ""
            if response.status_code == 200:
                subtitles = response.json()
                subtitles_content = " ".join([s["content"] for s in subtitles])
        
        # Index in Elasticsearch
        doc = {
            "id": video_id,
            "title": video_data["title"],
            "description": video_data.get("description", ""),
            "tags": video_data.get("tags", []),
            "subtitles": subtitles_content,
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
        
        return {"message": "Video indexed successfully"}
    except Exception as e:
        logger.error(f"Index error: {e}")
        raise HTTPException(status_code=500, detail="Failed to index video")

@app.delete("/search/index/{video_id}")
async def delete_from_index(
    video_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Remove a video from search index
    """
    try:
        await es_client.delete(index=settings.elasticsearch_index, id=video_id, ignore=[404])
        await es_client.indices.refresh(index=settings.elasticsearch_index)
        return {"message": "Video removed from index"}
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete from index")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
