from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import httpx
import json
import logging
import asyncio
from datetime import datetime

from .database import get_db, create_tables, Notification
from .config import settings
from .channel_events import dispatch_channel_event
from .smtp_send import send_email_sync
from .http_client import close_http_client, get_http_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()
internal_bearer = HTTPBearer(auto_error=True)


class NotificationCreate(BaseModel):
    user_id: str
    type: str
    message: str
    data: Optional[dict] = None


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    message: str
    data: Optional[dict]
    is_read: bool
    created_at: str


class ChannelEventPayload(BaseModel):
    event_type: str = Field(..., pattern="^(new_video|stream_live)$")
    channel_id: str
    owner_id: str
    channel_name: str = ""
    channel_handle: Optional[str] = None
    title: str
    entity_id: str
    link_path: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    logger.info("Notification service started")
    yield
    await close_http_client()
    logger.info("Notification service shutting down")


app = FastAPI(title="Notification Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if response.status_code == 200:
            return response.json()["id"]
        raise HTTPException(status_code=401, detail="Invalid token")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")


async def require_internal_token(
    credentials: HTTPAuthorizationCredentials = Depends(internal_bearer),
):
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Invalid internal token")
    return True


def _notification_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(n.id),
        user_id=str(n.user_id),
        type=n.type,
        message=n.message,
        data=json.loads(n.data) if n.data else None,
        is_read=n.is_read,
        created_at=str(n.created_at),
    )


async def send_email(to_email: str, subject: str, html_content: str):
    await asyncio.to_thread(send_email_sync, to_email, subject, html_content)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_notification(self, user_id: str, notification: dict):
        if user_id not in self.active_connections:
            return
        for connection in list(self.active_connections[user_id]):
            try:
                await connection.send_json(notification)
            except Exception:
                pass


manager = ConnectionManager()


class TestEmailPayload(BaseModel):
    to_email: str


@app.post("/internal/test-email")
async def internal_test_email(
    payload: TestEmailPayload,
    _ok: bool = Depends(require_internal_token),
):
    """Проверка SMTP без публикации видео/эфира."""
    ok = await asyncio.to_thread(
        send_email_sync,
        payload.to_email,
        "Тест уведомлений Видеохостинг ДГИ",
        "<p>Если вы видите это письмо, SMTP настроен верно.</p>",
    )
    if not ok:
        raise HTTPException(
            status_code=502,
            detail="SMTP send failed — см. логи notification-service (часто: пароль приложения Яндекса для «Почта»)",
        )
    return {"ok": True}


@app.post("/internal/events/channel")
async def internal_channel_event(
    payload: ChannelEventPayload,
    _ok: bool = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """Fan-out to channel subscribers (called by video-service / streaming-service)."""
    count = await dispatch_channel_event(
        db,
        event_type=payload.event_type,
        channel_id=payload.channel_id,
        owner_id=payload.owner_id,
        channel_name=payload.channel_name,
        channel_handle=payload.channel_handle,
        title=payload.title,
        entity_id=payload.entity_id,
        link_path=payload.link_path,
        push_ws=manager.send_notification,
        send_email_fn=send_email,
    )
    return {"notified_count": count}


@app.post("/notifications", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    notification = await Notification.create(
        db,
        user_id=notification_data.user_id,
        type=notification_data.type,
        message=notification_data.message,
        data=json.dumps(notification_data.data) if notification_data.data else None,
    )
    resp = _notification_response(notification)
    await manager.send_notification(str(notification.user_id), resp.model_dump())
    return resp


@app.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    skip: int = 0,
    limit: int = 20,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    notifications = await Notification.get_by_user_id(db, user_id, skip=skip, limit=limit)
    return [_notification_response(n) for n in notifications]


@app.put("/notifications/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    notification = await Notification.get_by_id(db, notification_id)
    if not notification or str(notification.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")

    await Notification.mark_as_read(db, notification_id)
    return {"message": "Notification marked as read"}


@app.post("/notifications/mark-all-read")
async def mark_all_as_read(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await Notification.mark_all_as_read(db, user_id)
    return {"message": "All notifications marked as read"}


@app.get("/notifications/unread-count")
async def get_unread_count(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    count = await Notification.get_unread_count(db, user_id)
    return {"unread_count": count}


@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.auth_service_url}/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            if response.status_code != 200:
                await websocket.close(code=1008)
                return
            user_id = response.json()["id"]
    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            await asyncio.sleep(settings.websocket_heartbeat)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
