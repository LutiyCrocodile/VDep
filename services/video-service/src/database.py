from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID, Integer, BigInteger, Interval, ARRAY, text
from typing import AsyncGenerator, List
import uuid
from datetime import datetime
from .config import settings

class Base(DeclarativeBase):
    pass

class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(String)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    duration = Column(Interval)
    resolution = Column(String(20))
    bitrate = Column(Integer)
    file_size = Column(BigInteger, nullable=False)
    minio_key = Column(String(255), unique=True, nullable=False)
    hls_playlist_url = Column(String(500))
    status = Column(String(20), default="uploaded")
    is_private = Column(Boolean, default=False)
    tags = Column(ARRAY(String))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        video_id = kwargs.get('id', uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO videos (id, title, description, user_id, duration, resolution, bitrate, file_size, minio_key, hls_playlist_url, status, is_private, tags, created_at, updated_at)
                VALUES (:id, :title, :description, :user_id, :duration, :resolution, :bitrate, :file_size, :minio_key, :hls_playlist_url, :status, :is_private, :tags, :created_at, :updated_at)
            """),
            {
                "id": video_id,
                "title": kwargs['title'],
                "description": kwargs.get('description'),
                "user_id": kwargs['user_id'],
                "duration": kwargs.get('duration'),
                "resolution": kwargs.get('resolution'),
                "bitrate": kwargs.get('bitrate'),
                "file_size": kwargs['file_size'],
                "minio_key": kwargs['minio_key'],
                "hls_playlist_url": kwargs.get('hls_playlist_url'),
                "status": kwargs.get('status', 'uploaded'),
                "is_private": kwargs.get('is_private', False),
                "tags": kwargs.get('tags', []),
                "created_at": kwargs.get('created_at', datetime.utcnow()),
                "updated_at": kwargs.get('updated_at', datetime.utcnow())
            }
        )
        await db.commit()
        return await cls.get_by_id(db, str(video_id))

    @classmethod
    async def get_by_id(cls, db: AsyncSession, video_id: str):
        result = await db.execute(text("SELECT * FROM videos WHERE id = :id"), {"id": video_id})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def get_all(cls, db: AsyncSession, skip: int = 0, limit: int = 10, user_id: str = None):
        if user_id:
            # For authenticated users, show their own videos + public videos
            query = """
                SELECT * FROM videos
                WHERE user_id = :user_id OR is_private = false
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """
            result = await db.execute(text(query), {"user_id": user_id, "limit": limit, "skip": skip})
        else:
            # For anonymous users, show only public videos
            query = """
                SELECT * FROM videos
                WHERE is_private = false
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """
            result = await db.execute(text(query), {"limit": limit, "skip": skip})

        rows = result.fetchall()
        return [cls(**row._asdict()) for row in rows]

    @classmethod
    async def update_status(cls, db: AsyncSession, video_id: str, status: str):
        await db.execute(
            text("UPDATE videos SET status = :status, updated_at = NOW() WHERE id = :id"),
            {"status": status, "id": video_id}
        )
        await db.commit()

    @classmethod
    async def update_metadata(cls, db: AsyncSession, video_id: str, **kwargs):
        update_fields = []
        params = {"id": video_id}

        for field in ['duration', 'resolution', 'bitrate', 'hls_playlist_url', 'status']:
            if field in kwargs:
                update_fields.append(f"{field} = :{field}")
                params[field] = kwargs[field]

        if update_fields:
            update_fields.append("updated_at = NOW()")
            query = f"UPDATE videos SET {', '.join(update_fields)} WHERE id = :id"
            await db.execute(text(query), params)
            await db.commit()

# Database engine
engine = create_async_engine(
    settings.database_url,
    echo=True,  # Set to False in production
    future=True
)

# Session factory
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
