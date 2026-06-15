from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.core.config import APP_NAME
from app.core.config import PORTAL_URL
from app.db.schema import ensure_schema
from app.db.base import Base
from app.db.session import engine
from app.routers import admin, auth, equipment, tickets
from app.routers import users, kb, notifications

logging.basicConfig(level=logging.INFO)

MEDIA_DIR = Path("app") / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)

# CORS configuration to allow requests from portal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002", "http://localhost:3000", "http://localhost:3005"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def _root_redirect(request: Request) -> Response:
    # For HTML requests, redirect to portal login. For API calls, return health check.
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept or accept == "*/*" or accept == "":
        return RedirectResponse(url=f"{PORTAL_URL.rstrip('/')}/login", status_code=303)
    return {"status": "ok", "service": APP_NAME}


@app.middleware("http")
async def portal_token_bridge(request, call_next):
    access_token = request.query_params.get("access_token")
    refresh_token = request.query_params.get("refresh_token")
    if access_token and refresh_token:
        if request.url.path == "/":
            clean_url = str(request.url.replace(path="/app", query=""))
        else:
            clean_url = str(request.url.replace(query=""))
        response = RedirectResponse(url=clean_url, status_code=307)
        response.set_cookie("support_access_token", access_token, max_age=60 * 60 * 24 * 7, samesite="lax")
        response.set_cookie("support_refresh_token", refresh_token, max_age=60 * 60 * 24 * 14, samesite="lax")
        return response
    return await call_next(request)


@app.exception_handler(HTTPException)
async def _http_exc_handler(request: Request, exc: HTTPException) -> Response:
    # For HTML pages, redirect to portal login on 401.
    if exc.status_code == 401:
        accept = (request.headers.get("accept") or "").lower()
        if "text/html" in accept or accept == "*/*" or accept == "":
            return RedirectResponse(url=f"{PORTAL_URL.rstrip('/')}/login", status_code=303)
    raise exc

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(equipment.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(kb.router)
app.include_router(notifications.router)
