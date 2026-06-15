import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uuid

from app.config import settings, validate_security_config
from app.database import init_db, async_session
from app.http_client import close_http_client
from app.middleware import register_middleware, register_exception_handlers
from app.services.backup import backup_worker
from app.routers import auth, chats, websocket, admin, calls, polls, notifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app")


async def scheduled_message_worker():
    """Background task: every 15s look for scheduled messages whose time has come and dispatch them."""
    from sqlalchemy import select
    from app.models.message import Message
    from app.models.chat import ChatMember
    from app.models.user import User
    from app.routers.websocket import manager

    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            now_naive = now_utc.replace(tzinfo=None)
            async with async_session() as session:
                # Берём всех кандидатов; сравниваем в Python, чтобы корректно обрабатывать
                # как timezone-aware, так и naive значения (SQLite хранит как строку).
                result = await session.execute(
                    select(Message).where(
                        Message.is_scheduled == True,
                        Message.scheduled_at != None,
                    )
                )
                candidates = result.scalars().all()
                due = []
                for msg in candidates:
                    sa = msg.scheduled_at
                    if sa is None:
                        continue
                    # Нормализуем: naive считаем UTC.
                    sa_cmp = sa if sa.tzinfo else sa.replace(tzinfo=timezone.utc)
                    if sa_cmp <= now_utc:
                        due.append(msg)
                for msg in due:
                    msg.is_scheduled = False
                    # Update created_at to actual dispatch moment so the message
                    # appears in chat with the real send time, not original creation.
                    msg.created_at = now_utc
                    sender = (await session.execute(select(User).where(User.id == msg.sender_id))).scalar_one_or_none()
                    members = (await session.execute(
                        select(ChatMember).where(ChatMember.chat_id == msg.chat_id)
                    )).scalars().all()
                    payload = {
                        "id": str(msg.id),
                        "chat_id": str(msg.chat_id),
                        "sender_id": str(msg.sender_id),
                        "sender_name": f"{sender.first_name} {sender.last_name}" if sender else "",
                        "sender_avatar": sender.avatar_url if sender else None,
                        "content": msg.content,
                        "message_type": msg.message_type,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        "is_edited": False,
                        "is_deleted": False,
                        "attachments": [],
                        "reactions": [],
                        "reply_to": None,
                        "poll": None,
                        "is_read": False,
                    }
                    recipient_ids = [str(m.user_id) for m in members]
                    await manager.send_to_users(recipient_ids, {
                        "type": "new_message",
                        "chat_id": str(msg.chat_id),
                        "message": payload,
                        "is_scheduled_dispatch": True,
                    })
                if due:
                    await session.commit()
                    print(f"[scheduled_message_worker] dispatched {len(due)} message(s)")
        except Exception as e:
            print(f"[scheduled_message_worker] error: {e}")
        await asyncio.sleep(15)


async def seed_data():
    """Seed initial data if DB is empty."""
    from sqlalchemy import select
    from app.models.user import Department
    from app.models.chat import Chat

    async with async_session() as session:
        result = await session.execute(select(Department).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        departments = [
            Department(id=uuid.UUID('00000000-0000-0000-0000-000000000001'), name='Управление информатизации', short_name='УИ'),
            Department(id=uuid.UUID('00000000-0000-0000-0000-000000000002'), name='Управление государственной службы и кадров', short_name='УГСК'),
            Department(id=uuid.UUID('00000000-0000-0000-0000-000000000003'), name='Управление имущества', short_name='УИм'),
            Department(id=uuid.UUID('00000000-0000-0000-0000-000000000004'), name='Управление земельных ресурсов', short_name='УЗР'),
            Department(id=uuid.UUID('00000000-0000-0000-0000-000000000005'), name='Правовое управление', short_name='ПУ'),
            Department(id=uuid.UUID('00000000-0000-0000-0000-000000000006'), name='Управление бухгалтерского учета и отчетности', short_name='УБУО'),
        ]
        for d in departments:
            session.add(d)

        news_result = await session.execute(select(Chat).where(Chat.is_news_channel == True).limit(1))
        if news_result.scalar_one_or_none() is None:
            session.add(Chat(
                id=uuid.UUID('00000000-0000-0000-0000-000000000100'),
                chat_type='channel',
                name='Новости ДГИ',
                description='Официальный новостной канал Департамента городского имущества',
                is_news_channel=True,
            ))

        await session.commit()
        print("✓ Справочник подразделений мессенджера загружен")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_security_config()
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    await init_db()
    await seed_data()
    worker_task = asyncio.create_task(scheduled_message_worker())
    backup_task = asyncio.create_task(backup_worker())
    logger.info("✓ Приложение запущено (env=%s)", settings.ENV)
    try:
        yield
    finally:
        await close_http_client()
        for t in (worker_task, backup_task):
            t.cancel()
        for t in (worker_task, backup_task):
            try:
                await t
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Корпоративный Мессенджер ДГИ",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Response-Time-Ms"],
)

# Подключаем обработчики ошибок, rate-limit, security headers, request_id, метрики
register_exception_handlers(app)
register_middleware(app)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(admin.router)
app.include_router(calls.router)
app.include_router(polls.router)
app.include_router(notifications.router)
app.include_router(websocket.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Корпоративный Мессенджер ДГИ"}
