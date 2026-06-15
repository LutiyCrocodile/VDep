import json
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth_client import auth_client
from app.database import async_session
from app.models.user import User

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active_connections

    async def send_to_user(self, user_id: str, data: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(user_id)

    async def send_to_users(self, user_ids: list, data: dict):
        for uid in user_ids:
            await self.send_to_user(uid, data)

    async def broadcast(self, data: dict):
        for uid in list(self.active_connections.keys()):
            await self.send_to_user(uid, data)


manager = ConnectionManager()


async def _set_user_status(user_id: str, online: bool):
    """Update user.status / last_seen in DB and broadcast presence event."""
    try:
        import uuid as uuid_mod
        async with async_session() as session:
            u_r = await session.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
            u = u_r.scalar_one_or_none()
            if u:
                u.status = "online" if online else "offline"
                u.last_seen = datetime.utcnow()
                await session.commit()
                ls = u.last_seen.isoformat() if u.last_seen else None
        await manager.broadcast({
            "type": "presence",
            "user_id": user_id,
            "status": "online" if online else "offline",
            "last_seen": ls if not online else None,
        })
    except Exception as e:
        print(f"[presence] error: {e}")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    auth_user = await auth_client.verify_token(token)
    if not auth_user:
        await websocket.close(code=4001)
        return
    user_id = auth_user["id"]

    await manager.connect(websocket, user_id)
    await _set_user_status(user_id, True)
    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "message":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "new_message",
                    "chat_id": data.get("chat_id"),
                    "message": data.get("message"),
                })

            elif event_type == "typing":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "typing",
                    "chat_id": data.get("chat_id"),
                    "user_id": user_id,
                })

            elif event_type == "stop_typing":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "stop_typing",
                    "chat_id": data.get("chat_id"),
                    "user_id": user_id,
                })

            elif event_type == "read":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "read",
                    "chat_id": data.get("chat_id"),
                    "user_id": user_id,
                })

            elif event_type == "call_signal":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "call_signal",
                    "call_id": data.get("call_id"),
                    "signal_type": data.get("signal_type"),
                    "signal": data.get("signal"),
                    "from_user": user_id,
                })

            elif event_type == "call_invite":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "call_invite",
                    "call_id": data.get("call_id"),
                    "call_type": data.get("call_type", "audio"),
                    "from_user": user_id,
                    "from_name": data.get("from_name", ""),
                    "from_avatar": data.get("from_avatar"),
                })

            elif event_type == "call_accept":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "call_accept",
                    "call_id": data.get("call_id"),
                    "from_user": user_id,
                })

            elif event_type == "call_reject":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "call_reject",
                    "call_id": data.get("call_id"),
                    "from_user": user_id,
                })

            elif event_type == "call_end":
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "call_end",
                    "call_id": data.get("call_id"),
                    "from_user": user_id,
                })

            elif event_type == "call_leave":
                # Участник покидает звонок - уведомляем остальных
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "call_leave",
                    "call_id": data.get("call_id"),
                    "from_user": data.get("from_user"),
                })

            elif event_type == "broadcast_started":
                # Трансляция отправляется всем подключённым пользователям
                call_id = data.get("call_id")
                if not call_id or call_id == "undefined":
                    print(f"[WebSocket] Invalid call_id in broadcast_started: {call_id}")
                    continue
                await manager.broadcast({
                    "type": "broadcast_started",
                    "call_id": call_id,
                    "call_type": data.get("call_type", "audio"),
                    "from_user": user_id,
                    "from_name": data.get("from_name", ""),
                    "from_avatar": data.get("from_avatar"),
                    "chat_id": data.get("chat_id"),
                })

            elif event_type == "broadcast_join_request":
                # Зритель запрашивает offer от ведущего трансляции
                recipients = data.get("recipients", [])
                await manager.send_to_users(recipients, {
                    "type": "broadcast_join_request",
                    "call_id": data.get("call_id"),
                    "from_user": data.get("from_user"),
                })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await _set_user_status(user_id, False)
