from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID, Integer, BigInteger, Interval, ARRAY, text
from typing import AsyncGenerator, List
import uuid
import logging
from datetime import datetime
from .config import settings

class Base(DeclarativeBase):
    pass

class Channel(Base):
    __tablename__ = "channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(String)
    handle = Column(String(50), unique=True, nullable=False)
    avatar_url = Column(String(500))
    banner_url = Column(String(500))
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    subscribers_count = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        channel_id = kwargs.get('id', uuid.uuid4())
        
        # Normalize all IDs to strings for asyncpg compatibility
        owner_id_raw = kwargs['owner_id']
        try:
            if isinstance(owner_id_raw, uuid.UUID):
                owner_id_str = str(owner_id_raw)
            else:
                owner_id_str = str(uuid.UUID(str(owner_id_raw)))
        except (ValueError, TypeError):
            owner_id_str = str(owner_id_raw)
        
        # Ensure channel_id is string
        if isinstance(channel_id, uuid.UUID):
            channel_id_str = str(channel_id)
        else:
            channel_id_str = str(channel_id)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Creating channel with owner_id (str): {owner_id_str}")
        
        await db.execute(
            text("""
                INSERT INTO channels (id, name, description, handle, avatar_url, banner_url, owner_id, subscribers_count, is_verified, created_at, updated_at)
                VALUES (:id, :name, :description, :handle, :avatar_url, :banner_url, :owner_id, :subscribers_count, :is_verified, :created_at, :updated_at)
            """),
            {
                "id": channel_id_str,
                "name": kwargs['name'],
                "description": kwargs.get('description'),
                "handle": kwargs['handle'],
                "avatar_url": kwargs.get('avatar_url'),
                "banner_url": kwargs.get('banner_url'),
                "owner_id": owner_id_str,
                "subscribers_count": kwargs.get('subscribers_count', 0),
                "is_verified": kwargs.get('is_verified', False),
                "created_at": kwargs.get('created_at', datetime.utcnow()),
                "updated_at": kwargs.get('updated_at', datetime.utcnow())
            }
        )
        await db.commit()
        return await cls.get_by_id(db, channel_id_str)

    @classmethod
    async def get_by_id(cls, db: AsyncSession, channel_id: str):
        result = await db.execute(text("SELECT * FROM channels WHERE id = :id"), {"id": channel_id})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def get_by_owner(cls, db: AsyncSession, owner_id: str):
        owner_id_str = str(owner_id).strip()
        logger = logging.getLogger(__name__)
        logger.info(f"Looking up channel by owner_id: '{owner_id_str}'")
        
        # Normalize UUID format - try both with and without hyphens
        try:
            # Convert to UUID object for consistent comparison
            if isinstance(owner_id, uuid.UUID):
                owner_uuid = owner_id
            else:
                # Remove hyphens if present, then parse
                clean_id = owner_id_str.replace('-', '')
                if len(clean_id) == 32:
                    owner_uuid = uuid.UUID(clean_id)
                else:
                    owner_uuid = uuid.UUID(owner_id_str)
            
            # Use direct UUID comparison - PostgreSQL auto-converts string to UUID
            result = await db.execute(
                text("SELECT * FROM channels WHERE owner_id = :owner_id"),
                {"owner_id": str(owner_uuid)}
            )
            row = result.first()
            if row:
                logger.info(f"Found channel: {row._asdict()}")
                return cls(**row._asdict())
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse owner_id as UUID: {e}")
            # Fallback to string comparison if UUID parsing fails
            result = await db.execute(
                text("SELECT * FROM channels WHERE owner_id::text = :owner_id"),
                {"owner_id": owner_id_str}
            )
            row = result.first()
            if row:
                logger.info(f"Found channel with string comparison: {row._asdict()}")
                return cls(**row._asdict())
        
        # Debug: show what we searched for and what's in DB
        debug_result = await db.execute(
            text("SELECT id, owner_id::text as owner_id, name FROM channels")
        )
        debug_rows = debug_result.fetchall()
        logger.warning(f"No channel found for owner_id: '{owner_id_str}'")
        debug_data = [row._asdict() for row in debug_rows]
        logger.warning(f"All channels in DB: {debug_data}")
        return None

    @classmethod
    async def get_by_handle(cls, db: AsyncSession, handle: str):
        result = await db.execute(text("SELECT * FROM channels WHERE handle = :handle"), {"handle": handle})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def increment_subscribers(cls, db: AsyncSession, channel_id: str):
        await db.execute(
            text("UPDATE channels SET subscribers_count = subscribers_count + 1 WHERE id = :id"),
            {"id": channel_id}
        )
        await db.commit()

    @classmethod
    async def decrement_subscribers(cls, db: AsyncSession, channel_id: str):
        await db.execute(
            text("UPDATE channels SET subscribers_count = GREATEST(subscribers_count - 1, 0) WHERE id = :id"),
            {"id": channel_id}
        )
        await db.commit()

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscriber_id = Column(UUID(as_uuid=True), nullable=False)
    channel_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        sub_id = kwargs.get('id', uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO subscriptions (id, subscriber_id, channel_id, created_at)
                VALUES (:id, :subscriber_id, :channel_id, :created_at)
            """),
            {
                "id": sub_id,
                "subscriber_id": kwargs['subscriber_id'],
                "channel_id": kwargs['channel_id'],
                "created_at": kwargs.get('created_at', datetime.utcnow())
            }
        )
        await db.commit()
        await Channel.increment_subscribers(db, kwargs['channel_id'])
        return await cls.get_by_id(db, str(sub_id))

    @classmethod
    async def delete(cls, db: AsyncSession, subscriber_id: str, channel_id: str):
        await db.execute(
            text("DELETE FROM subscriptions WHERE subscriber_id = :subscriber_id AND channel_id = :channel_id"),
            {"subscriber_id": subscriber_id, "channel_id": channel_id}
        )
        await db.commit()
        await Channel.decrement_subscribers(db, channel_id)

    @classmethod
    async def get_by_id(cls, db: AsyncSession, sub_id: str):
        result = await db.execute(text("SELECT * FROM subscriptions WHERE id = :id"), {"id": sub_id})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def is_subscribed(cls, db: AsyncSession, subscriber_id: str, channel_id: str) -> bool:
        result = await db.execute(
            text("SELECT COUNT(*) FROM subscriptions WHERE subscriber_id = :subscriber_id AND channel_id = :channel_id"),
            {"subscriber_id": subscriber_id, "channel_id": channel_id}
        )
        count = result.scalar()
        return count > 0

    @classmethod
    async def get_user_subscriptions(cls, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 10):
        query = """
            SELECT c.* FROM channels c
            INNER JOIN subscriptions s ON c.id = s.channel_id
            WHERE s.subscriber_id = :user_id
            ORDER BY s.created_at DESC
            LIMIT :limit OFFSET :skip
        """
        result = await db.execute(text(query), {"user_id": user_id, "limit": limit, "skip": skip})
        rows = result.fetchall()
        return [Channel(**row._asdict()) for row in rows]

    @classmethod
    async def get_channel_subscribers(cls, db: AsyncSession, channel_id: str, skip: int = 0, limit: int = 10):
        query = """
            SELECT u.* FROM users u
            INNER JOIN subscriptions s ON u.id = s.subscriber_id
            WHERE s.channel_id = :channel_id
            ORDER BY s.created_at DESC
            LIMIT :limit OFFSET :skip
        """
        result = await db.execute(text(query), {"channel_id": channel_id, "limit": limit, "skip": skip})
        rows = result.fetchall()
        return rows

class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(String)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    channel_id = Column(UUID(as_uuid=True))
    duration = Column(Interval)
    resolution = Column(String(20))
    bitrate = Column(Integer)
    file_size = Column(BigInteger, nullable=False)
    minio_key = Column(String(255), unique=True, nullable=False)
    hls_playlist_url = Column(String(500))
    status = Column(String(20), default="uploaded")
    is_private = Column(Boolean, default=False)
    tags = Column(ARRAY(String))
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        video_id = kwargs.get('id', uuid.uuid4())
        # Ensure all UUIDs are strings for asyncpg
        video_id_str = str(video_id) if isinstance(video_id, uuid.UUID) else str(video_id)
        user_id_str = str(kwargs['user_id']) if isinstance(kwargs['user_id'], uuid.UUID) else str(kwargs['user_id'])
        channel_id_str = str(kwargs.get('channel_id')) if kwargs.get('channel_id') else None
        
        await db.execute(
            text("""
                INSERT INTO videos (id, title, description, user_id, channel_id, duration, resolution, bitrate, file_size, minio_key, hls_playlist_url, status, is_private, tags, created_at, updated_at)
                VALUES (:id, :title, :description, :user_id, :channel_id, :duration, :resolution, :bitrate, :file_size, :minio_key, :hls_playlist_url, :status, :is_private, :tags, :created_at, :updated_at)
            """),
            {
                "id": video_id_str,
                "title": kwargs['title'],
                "description": kwargs.get('description'),
                "user_id": user_id_str,
                "channel_id": channel_id_str,
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
        return await cls.get_by_id(db, video_id_str)

    @classmethod
    async def get_by_id(cls, db: AsyncSession, video_id: str):
        result = await db.execute(text("SELECT * FROM videos WHERE id = :id"), {"id": video_id})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def get_all(cls, db: AsyncSession, skip: int = 0, limit: int = 10, user_id: str = None, channel_id: str = None):
        if channel_id:
            query = """
                SELECT * FROM videos
                WHERE channel_id = :channel_id AND is_private = false
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """
            result = await db.execute(text(query), {"channel_id": channel_id, "limit": limit, "skip": skip})
        elif user_id:
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
    async def increment_views(cls, db: AsyncSession, video_id: str):
        await db.execute(
            text("UPDATE videos SET views_count = views_count + 1 WHERE id = :id"),
            {"id": video_id}
        )
        await db.commit()

    @classmethod
    async def update_metadata(cls, db: AsyncSession, video_id: str, **kwargs):
        update_fields = []
        params = {"id": video_id}

        for field in ['duration', 'resolution', 'bitrate', 'hls_playlist_url', 'status', 'channel_id']:
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
