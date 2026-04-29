from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID, text
from typing import AsyncGenerator
import uuid
from datetime import datetime
from .config import settings

class Base(DeclarativeBase):
    pass

class Stream(Base):
    __tablename__ = "streams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(String)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    rtmp_key = Column(String(255), unique=True, nullable=False)
    hls_url = Column(String(500))
    is_live = Column(Boolean, default=False)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    archived_video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"))
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        stream_id = uuid.uuid4()
        await db.execute(
            text("""
                INSERT INTO streams (id, title, description, user_id, rtmp_key, hls_url, is_live, start_time, end_time, archived_video_id, is_private, created_at)
                VALUES (:id, :title, :description, :user_id, :rtmp_key, :hls_url, :is_live, :start_time, :end_time, :archived_video_id, :is_private, :created_at)
            """),
            {
                "id": stream_id,
                "title": kwargs['title'],
                "description": kwargs.get('description'),
                "user_id": kwargs['user_id'],
                "rtmp_key": kwargs['rtmp_key'],
                "hls_url": kwargs.get('hls_url'),
                "is_live": kwargs.get('is_live', False),
                "start_time": kwargs.get('start_time'),
                "end_time": kwargs.get('end_time'),
                "archived_video_id": kwargs.get('archived_video_id'),
                "is_private": kwargs.get('is_private', False),
                "created_at": kwargs.get('created_at', datetime.utcnow())
            }
        )
        await db.commit()
        return await cls.get_by_id(db, str(stream_id))

    @classmethod
    async def get_by_id(cls, db: AsyncSession, stream_id: str):
        result = await db.execute(text("SELECT * FROM streams WHERE id = :id"), {"id": stream_id})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def get_all(cls, db: AsyncSession, user_id: str = None):
        if user_id:
            query = """
                SELECT * FROM streams
                WHERE user_id = :user_id OR is_private = false
                ORDER BY created_at DESC
            """
            result = await db.execute(text(query), {"user_id": user_id})
        else:
            query = """
                SELECT * FROM streams
                WHERE is_private = false
                ORDER BY created_at DESC
            """
            result = await db.execute(text(query))

        rows = result.fetchall()
        return [cls(**row._asdict()) for row in rows]

    @classmethod
    async def update_status(cls, db: AsyncSession, stream_id: str, is_live: bool = None, start_time: datetime = None, end_time: datetime = None, hls_url: str = None, archived_video_id: str = None):
        update_fields = []
        params = {"id": stream_id}

        if is_live is not None:
            update_fields.append("is_live = :is_live")
            params["is_live"] = is_live

        if start_time is not None:
            update_fields.append("start_time = :start_time")
            params["start_time"] = start_time

        if end_time is not None:
            update_fields.append("end_time = :end_time")
            params["end_time"] = end_time

        if hls_url is not None:
            update_fields.append("hls_url = :hls_url")
            params["hls_url"] = hls_url

        if archived_video_id is not None:
            update_fields.append("archived_video_id = :archived_video_id")
            params["archived_video_id"] = archived_video_id

        if update_fields:
            query = f"UPDATE streams SET {', '.join(update_fields)} WHERE id = :id"
            await db.execute(text(query), params)
            await db.commit()

    @classmethod
    async def get_by_rtmp_key(cls, db: AsyncSession, rtmp_key: str):
        result = await db.execute(text("SELECT * FROM streams WHERE rtmp_key = :rtmp_key"), {"rtmp_key": rtmp_key})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def get_live_streams(cls, db: AsyncSession):
        result = await db.execute(text("SELECT * FROM streams WHERE is_live = true ORDER BY start_time DESC"))
        rows = result.fetchall()
        return [cls(**row._asdict()) for row in rows]

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
