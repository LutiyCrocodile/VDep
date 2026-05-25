"""Video service — FastAPI entrypoint."""
from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from minio.error import S3Error

from .config import settings
from .database import create_tables
from .deps import minio_client
from .http_client import close_http_client
from .routers import channels, health, internal, media, videos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    try:
        if not minio_client.bucket_exists(settings.minio_bucket):
            minio_client.make_bucket(settings.minio_bucket)
            logger.info("Created MinIO bucket: %s", settings.minio_bucket)
    except S3Error as e:
        logger.error("MinIO error: %s", e)
    logger.info("Video service started")
    yield
    await close_http_client()
    logger.info("Video service shutting down")


app = FastAPI(title="Video Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(internal.router)
app.include_router(media.router)
app.include_router(videos.router)
app.include_router(channels.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
