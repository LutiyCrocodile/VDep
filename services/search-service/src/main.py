from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uvicorn
from pydantic import BaseModel
from typing import Optional, List, Any
import httpx
import logging
from elasticsearch import AsyncElasticsearch

from .database import get_db, create_tables, Subtitle
from .config import settings
from .http_client import close_http_client, get_http_client
from .search_query import build_search_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)
user_bearer = HTTPBearer()
internal_bearer = HTTPBearer(auto_error=True)

es_client = AsyncElasticsearch([settings.elasticsearch_hosts])


class VideoSearchResult(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    duration: Optional[Any] = None
    resolution: Optional[str] = None
    file_size: int = 0
    status: str = "ready"
    hls_playlist_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_private: bool = False
    tags: List[str] = []
    created_at: str
    user_id: str
    views_count: int = 0
    classification: str = "public"
    relevance_score: float = 0.0
    highlights: Optional[dict] = None


class SearchResponse(BaseModel):
    results: List[VideoSearchResult]
    total: int


class SubtitleResponse(BaseModel):
    id: str
    video_id: str
    language: str
    content: str
    created_at: str


async def require_internal_token(
    credentials: HTTPAuthorizationCredentials = Depends(internal_bearer),
):
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Invalid internal token")
    return True


def _public_media_url(object_path: Optional[str], video_id: str) -> Optional[str]:
    """Тот же формат, что video-service get_thumbnail_url → /media/..."""
    path = (object_path or "").strip()
    if not path:
        path = f"{video_id}/thumbnail.jpg"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    key = path.lstrip("/")
    if settings.public_media_via_api:
        return f"{settings.public_video_api_url.rstrip('/')}/media/{key}"
    return path


def _serialize_duration(duration_val) -> Optional[str]:
    if duration_val is None:
        return None
    if hasattr(duration_val, "total_seconds"):
        secs = int(duration_val.total_seconds())
        return str(secs)
    return str(duration_val)


async def _fetch_video_row(db: AsyncSession, video_id: str):
    result = await db.execute(
        text(
            """
            SELECT id, title, description, duration, resolution, file_size, status,
                   hls_playlist_url, thumbnail_url, is_private, tags, user_id,
                   created_at, views_count, classification
            FROM videos WHERE id = :id
            """
        ),
        {"id": video_id},
    )
    return result.first()


async def _remove_from_index(video_id: str) -> None:
    try:
        await es_client.delete(index=settings.elasticsearch_index, id=video_id, ignore=[404])
    except Exception as exc:
        logger.warning("ES delete %s: %s", video_id, exc)


async def _index_video_document(db: AsyncSession, video_id: str) -> None:
    row = await _fetch_video_row(db, video_id)
    if not row:
        await _remove_from_index(video_id)
        raise HTTPException(status_code=404, detail="Video not found")

    if (row.status or "") != "ready":
        await _remove_from_index(video_id)
        return

    subtitles = await Subtitle.get_by_video_id(db, video_id)
    subtitles_content = " ".join(s.content for s in subtitles if s.content)

    tags = row.tags if row.tags else []
    if isinstance(tags, str):
        tags = [tags]

    doc = {
        "id": str(row.id),
        "title": row.title or "",
        "description": row.description or "",
        "tags": list(tags),
        "subtitles": subtitles_content,
        "duration": _serialize_duration(row.duration),
        "resolution": row.resolution,
        "file_size": row.file_size or 0,
        "status": row.status or "ready",
        "hls_playlist_url": row.hls_playlist_url,
        "thumbnail_url": _public_media_url(row.thumbnail_url, str(row.id)),
        "is_private": bool(row.is_private),
        "user_id": str(row.user_id),
        "created_at": str(row.created_at),
        "views_count": row.views_count or 0,
        "classification": row.classification or "public",
    }

    await es_client.index(index=settings.elasticsearch_index, id=video_id, document=doc)


async def _filter_results_to_existing_ready(
    db: AsyncSession,
    results: List[VideoSearchResult],
    orphan_ids: List[str],
) -> tuple[List[VideoSearchResult], int]:
    """Убирает из выдачи удалённые / не ready; помечает сирот в ES для удаления."""
    if not results:
        return [], 0
    ids = [r.id for r in results]
    rows = await db.execute(
        text(
            """
            SELECT id::text FROM videos
            WHERE status = 'ready' AND id::text = ANY(CAST(:ids AS text[]))
            """
        ),
        {"ids": ids},
    )
    valid = {row[0] for row in rows.fetchall()}
    filtered = []
    for item in results:
        if item.id in valid:
            filtered.append(item)
        else:
            orphan_ids.append(item.id)
    return filtered, len(filtered)


async def _prune_orphan_index_entries(db: AsyncSession) -> int:
    """Удалить из ES документы без соответствующего ready-видео в БД."""
    result = await db.execute(text("SELECT id::text FROM videos WHERE status = 'ready'"))
    valid_ids = {row[0] for row in result.fetchall()}
    removed = 0
    search_after = None
    while True:
        body: dict = {"query": {"match_all": {}}, "_source": False, "size": 500, "sort": ["_doc"]}
        if search_after:
            body["search_after"] = search_after
        resp = await es_client.search(index=settings.elasticsearch_index, body=body)
        hits = resp["hits"]["hits"]
        if not hits:
            break
        for hit in hits:
            vid = hit["_id"]
            if vid not in valid_ids:
                await _remove_from_index(vid)
                removed += 1
        search_after = hits[-1]["sort"]
        if len(hits) < 500:
            break
    return removed


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await es_client.ping()
    if not await es_client.indices.exists(index=settings.elasticsearch_index):
        await es_client.indices.create(
            index=settings.elasticsearch_index,
            body={
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 512},
                            },
                        },
                        "description": {"type": "text"},
                        "tags": {"type": "keyword"},
                        "subtitles": {"type": "text"},
                        "status": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "is_private": {"type": "boolean"},
                    }
                }
            },
        )
    logger.info("Search service started")
    yield
    await es_client.close()
    await close_http_client()
    logger.info("Search service shutting down")


app = FastAPI(title="Search Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/search", response_model=SearchResponse)
async def search_videos(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    tags: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Полнотекстовый поиск. JWT опционален — без токена только public."""
    try:
        user_id = None
        if credentials:
            client = get_http_client()
            try:
                response = await client.get(
                    f"{settings.auth_service_url}/users/me",
                    headers={"Authorization": f"Bearer {credentials.credentials}"},
                )
                if response.status_code == 200:
                    user_id = response.json()["id"]
            except httpx.RequestError:
                pass

        search_body = {
            "from": skip,
            "size": limit,
            "track_total_hits": True,
            "query": build_search_query(q, user_id=user_id, tags=tags),
            "highlight": {
                "fields": {"title": {}, "description": {}, "subtitles": {}},
                "require_field_match": False,
            },
        }

        response = await es_client.search(index=settings.elasticsearch_index, body=search_body)

        results = []
        orphan_ids: List[str] = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            highlights = hit.get("highlight", {})
            results.append(
                VideoSearchResult(
                    id=source["id"],
                    title=source["title"],
                    description=source.get("description"),
                    duration=source.get("duration"),
                    resolution=source.get("resolution"),
                    file_size=source.get("file_size", 0),
                    status=source.get("status", "ready"),
                    hls_playlist_url=source.get("hls_playlist_url"),
                    thumbnail_url=source.get("thumbnail_url"),
                    is_private=source.get("is_private", False),
                    tags=source.get("tags", []),
                    created_at=source["created_at"],
                    user_id=source["user_id"],
                    views_count=source.get("views_count", 0),
                    classification=source.get("classification", "public"),
                    relevance_score=hit["_score"],
                    highlights=highlights,
                )
            )

        results, total = await _filter_results_to_existing_ready(db, results, orphan_ids)
        for vid in orphan_ids:
            await _remove_from_index(vid)

        return SearchResponse(results=results, total=total)
    except Exception as e:
        logger.error("Search error: %s", e)
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/videos/{video_id}/subtitles", response_model=List[SubtitleResponse])
async def get_subtitles(
    video_id: str,
    language: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(user_bearer),
):
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    subtitles = await Subtitle.get_by_video_id(db, video_id)
    if language:
        subtitles = [s for s in subtitles if s.language == language]

    return [
        SubtitleResponse(
            id=str(s.id),
            video_id=str(s.video_id),
            language=s.language,
            content=s.content,
            created_at=str(s.created_at),
        )
        for s in subtitles
    ]


@app.post("/internal/search/index/{video_id}")
async def internal_index_video(
    video_id: str,
    _ok: bool = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """Индексация после транскодинга (video-service / celery)."""
    try:
        await _index_video_document(db, video_id)
        return {"message": "Video indexed successfully", "video_id": video_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Internal index error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to index video")


@app.post("/internal/search/reindex-ready")
async def internal_reindex_ready(
    _ok: bool = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """Переиндексация всех ready-видео (dev / после пустого ES)."""
    result = await db.execute(text("SELECT id::text FROM videos WHERE status = 'ready'"))
    ids = [row[0] for row in result.fetchall()]
    indexed = 0
    errors = 0
    for vid in ids:
        try:
            await _index_video_document(db, vid)
            indexed += 1
        except Exception as e:
            errors += 1
            logger.warning("reindex skip %s: %s", vid, e)
    try:
        await es_client.indices.refresh(index=settings.elasticsearch_index)
    except Exception:
        pass
    pruned = await _prune_orphan_index_entries(db)
    return {
        "indexed": indexed,
        "total_ready": len(ids),
        "errors": errors,
        "pruned_orphans": pruned,
    }


@app.delete("/internal/search/index/{video_id}")
async def internal_delete_from_index(
    video_id: str,
    _ok: bool = Depends(require_internal_token),
):
    """Снятие с индекса при удалении видео (video-service)."""
    await _remove_from_index(video_id)
    return {"message": "Video removed from index", "video_id": video_id}


@app.post("/internal/search/prune-orphans")
async def internal_prune_orphans(
    _ok: bool = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """Удалить из ES записи удалённых / не ready видео."""
    pruned = await _prune_orphan_index_entries(db)
    try:
        await es_client.indices.refresh(index=settings.elasticsearch_index)
    except Exception:
        pass
    return {"pruned_orphans": pruned}


@app.post("/search/index/{video_id}")
async def index_video_user(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(user_bearer),
):
    """Ручная переиндексация (JWT пользователя)."""
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    try:
        await _index_video_document(db, video_id)
        return {"message": "Video indexed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Index error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to index video")


@app.delete("/search/index/{video_id}")
async def delete_from_index(
    video_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(user_bearer),
):
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    try:
        await es_client.delete(index=settings.elasticsearch_index, id=video_id, ignore=[404])
        return {"message": "Video removed from index"}
    except Exception as e:
        logger.error("Delete error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to delete from index")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
