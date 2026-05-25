"""Streaming service — FastAPI entrypoint."""
from contextlib import asynccontextmanager
import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables
from .http_client import close_http_client
from .rtmp import rtmp_reconcile_loop
from .routers import health, internal, streams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    reconcile_task = asyncio.create_task(rtmp_reconcile_loop())
    logger.info("Streaming service started")
    yield
    reconcile_task.cancel()
    try:
        await reconcile_task
    except asyncio.CancelledError:
        pass
    await close_http_client()
    logger.info("Streaming service shutting down")


app = FastAPI(title="Streaming Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(internal.router)
app.include_router(streams.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
