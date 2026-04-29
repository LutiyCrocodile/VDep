from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, DateTime, ForeignKey, UUID, Text, text
from typing import AsyncGenerator
import uuid
from datetime import datetime
from .config import settings

class Base(DeclarativeBase):
    pass

class Subtitle(Base):
    __tablename__ = "subtitles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    language = Column(String(10), default="ru")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def get_by_video_id(cls, db: AsyncSession, video_id: str):
        result = await db.execute(
            text("SELECT * FROM subtitles WHERE video_id = :video_id"),
            {"video_id": video_id}
        )
        rows = result.fetchall()
        return [cls(**row._asdict()) for row in rows]

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        subtitle_id = uuid.uuid4()
        await db.execute(
            text("""
                INSERT INTO subtitles (id, video_id, language, content, created_at)
                VALUES (:id, :video_id, :language, :content, :created_at)
            """),
            {
                "id": subtitle_id,
                "video_id": kwargs['video_id'],
                "language": kwargs.get('language', 'ru'),
                "content": kwargs['content'],
                "created_at": kwargs.get('created_at', datetime.utcnow())
            }
        )
        await db.commit()
        return await cls.get_by_id(db, str(subtitle_id))

    @classmethod
    async def get_by_id(cls, db: AsyncSession, subtitle_id: str):
        result = await db.execute(text("SELECT * FROM subtitles WHERE id = :id"), {"id": subtitle_id})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

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
