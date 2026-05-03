from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID, text
from typing import AsyncGenerator
import uuid
from datetime import datetime
from .config import settings

class Base(DeclarativeBase):
    pass

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    type = Column(String(50), nullable=False)
    message = Column(String, nullable=False)
    data = Column(String)  # JSON string
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        notification_id = uuid.uuid4()
        await db.execute(
            text("""
                INSERT INTO notifications (id, user_id, type, message, data, is_read, created_at)
                VALUES (:id, :user_id, :type, :message, :data, :is_read, :created_at)
            """),
            {
                "id": notification_id,
                "user_id": kwargs['user_id'],
                "type": kwargs['type'],
                "message": kwargs['message'],
                "data": kwargs.get('data'),
                "is_read": kwargs.get('is_read', False),
                "created_at": kwargs.get('created_at', datetime.utcnow())
            }
        )
        await db.commit()
        return await cls.get_by_id(db, str(notification_id))

    @classmethod
    async def get_by_id(cls, db: AsyncSession, notification_id: str):
        result = await db.execute(text("SELECT * FROM notifications WHERE id = :id"), {"id": notification_id})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def get_by_user_id(cls, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 20):
        query = """
            SELECT * FROM notifications
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """
        result = await db.execute(text(query), {"user_id": user_id, "limit": limit, "skip": skip})
        rows = result.fetchall()
        return [cls(**row._asdict()) for row in rows]

    @classmethod
    async def mark_as_read(cls, db: AsyncSession, notification_id: str):
        await db.execute(
            text("UPDATE notifications SET is_read = TRUE WHERE id = :id"),
            {"id": notification_id}
        )
        await db.commit()

    @classmethod
    async def mark_all_as_read(cls, db: AsyncSession, user_id: str):
        await db.execute(
            text("UPDATE notifications SET is_read = TRUE WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        await db.commit()

    @classmethod
    async def get_unread_count(cls, db: AsyncSession, user_id: str):
        result = await db.execute(
            text("SELECT COUNT(*) as count FROM notifications WHERE user_id = :user_id AND is_read = FALSE"),
            {"user_id": user_id}
        )
        row = result.first()
        return row.count if row else 0

engine = create_async_engine(
    settings.database_url,
    echo=True,
    future=True
)

async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
