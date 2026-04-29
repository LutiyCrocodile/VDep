from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
from pydantic import BaseModel
from typing import Optional, List, Dict
import httpx
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from datetime import datetime

from .database import get_db, create_tables
from .models import Notification
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    logger.info("Notification service started")
    yield
    logger.info("Notification service shutting down")

app = FastAPI(title="Notification Service", version="1.0.0", lifespan=lifespan)

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

@app.post("/notifications")
async def create_notification(
    notification_data: NotificationCreate,
    db: AsyncSession = Depends(get_db)
):
    notification = await Notification.create(
        db,
        user_id=notification_data.user_id,
        type=notification_data.type,
        message=notification_data.message,
        data=json.dumps(notification_data.data) if notification_data.data else None
    )
    return NotificationResponse(
        id=str(notification.id),
        user_id=str(notification.user_id),
        type=notification.type,
        message=notification.message,
        data=json.loads(notification.data) if notification.data else None,
        is_read=notification.is_read,
        created_at=str(notification.created_at)
    )

@app.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    skip: int = 0,
    limit: int = 20,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    notifications = await Notification.get_by_user_id(db, user_id, skip=skip, limit=limit)
    return [
        NotificationResponse(
            id=str(n.id),
            user_id=str(n.user_id),
            type=n.type,
            message=n.message,
            data=json.loads(n.data) if n.data else None,
            is_read=n.is_read,
            created_at=str(n.created_at)
        ) for n in notifications
    ]

@app.put("/notifications/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    notification = await Notification.get_by_id(db, notification_id)
    if not notification or str(notification.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    await Notification.mark_as_read(db, notification_id)
    return {"message": "Notification marked as read"}

@app.post("/notifications/mark-all-read")
async def mark_all_as_read(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    await Notification.mark_all_as_read(db, user_id)
    return {"message": "All notifications marked as read"}

@app.get("/notifications/unread-count")
async def get_unread_count(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    count = await Notification.get_unread_count(db, user_id)
    return {"unread_count": count}

# Email sending function
async def send_email(to_email: str, subject: str, html_content: str):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.smtp_from_email
        msg['To'] = to_email

        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_notification(self, user_id: str, notification: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(notification)
                except:
                    pass

manager = ConnectionManager()

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Validate token
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.auth_service_url}/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code != 200:
                await websocket.close(code=1008)
                return
            
            user_data = response.json()
            user_id = user_data["id"]
    except:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
