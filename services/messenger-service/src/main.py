"""
Messenger Service - Защищенный корпоративный мессенджер ДГИ
FastAPI application with JWT authentication and RBAC
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
from typing import Optional, List
import os
import logging

from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Messenger service started on port {settings.port}")
    yield
    logger.info("Messenger service shutting down")


app = FastAPI(title="Messenger Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str


# In-memory storage (demo)
chats_db = {}
messages_db = {}


async def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = auth_header.split(" ")[1]
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.auth_service_url}/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            user_data = response.json()
            messenger_perms = user_data.get("services", {}).get("messenger", {})
            if not messenger_perms or not messenger_perms.get("role"):
                raise HTTPException(status_code=403, detail="No access to messenger")
            
            return user_data
    except ImportError:
        import requests
        response = requests.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("src/static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", service="messenger")


@app.get("/api/chats")
async def get_chats(user: dict = Depends(verify_token)):
    user_id = user["id"]
    user_chats = [
        chat for chat in chats_db.values()
        if user_id in chat.get("participants", []) or chat.get("created_by") == user_id
    ]
    return {"chats": user_chats}


@app.post("/api/chats")
async def create_chat(chat_data: dict, user: dict = Depends(verify_token)):
    from uuid import uuid4
    
    chat_id = str(uuid4())
    chat = {
        "id": chat_id,
        "name": chat_data.get("name", "Новый чат"),
        "is_group": chat_data.get("is_group", False),
        "created_by": user["id"],
        "participants": [user["id"]] + chat_data.get("participants", []),
        "created_at": "2024-01-01T00:00:00Z"
    }
    chats_db[chat_id] = chat
    return chat


@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, user: dict = Depends(verify_token)):
    if chat_id not in chats_db:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    chat = chats_db[chat_id]
    user_id = user["id"]
    
    if user_id not in chat.get("participants", []) and chat.get("created_by") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    chat_messages = [
        msg for msg in messages_db.values()
        if msg.get("chat_id") == chat_id
    ]
    return {"messages": chat_messages}


@app.post("/api/chats/{chat_id}/messages")
async def send_message(chat_id: str, message_data: dict, user: dict = Depends(verify_token)):
    from uuid import uuid4
    from datetime import datetime
    
    if chat_id not in chats_db:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    chat = chats_db[chat_id]
    user_id = user["id"]
    
    if user_id not in chat.get("participants", []) and chat.get("created_by") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    msg_id = str(uuid4())
    message = {
        "id": msg_id,
        "chat_id": chat_id,
        "sender_id": user_id,
        "text": message_data.get("text", ""),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    messages_db[msg_id] = message
    return message


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("MESSENGER_SERVICE_PORT", 3001)),
        reload=True
    )
