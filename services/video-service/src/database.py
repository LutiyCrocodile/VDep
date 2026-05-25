from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID, Integer, BigInteger, Interval, ARRAY, text, UniqueConstraint
from typing import AsyncGenerator, List
import uuid
import logging
from datetime import datetime
from .config import settings

logger = logging.getLogger(__name__)


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
    async def get_by_ids(cls, db: AsyncSession, channel_ids: list[str]) -> dict[str, "Channel"]:
        if not channel_ids:
            return {}
        unique_ids = list({str(cid) for cid in channel_ids})
        result = await db.execute(
            text("SELECT * FROM channels WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": unique_ids},
        )
        out: dict[str, Channel] = {}
        for row in result.fetchall():
            ch = cls(**row._asdict())
            out[str(ch.id)] = ch
        return out

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
    async def get_channel_subscriber_ids(cls, db: AsyncSession, channel_id: str) -> list:
        result = await db.execute(
            text(
                "SELECT subscriber_id::text FROM subscriptions WHERE channel_id = CAST(:channel_id AS uuid)"
            ),
            {"channel_id": channel_id},
        )
        return [str(row[0]) for row in result.fetchall()]

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

class Classification(Base):
    __tablename__ = "classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False, default=1)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def get_all(cls, db: AsyncSession):
        result = await db.execute(text("SELECT * FROM classifications ORDER BY level"))
        rows = result.fetchall()
        return [cls(**row._asdict()) for row in rows]

    @classmethod
    async def get_by_id(cls, db: AsyncSession, classification_id: str):
        result = await db.execute(
            text("SELECT * FROM classifications WHERE id = :id"),
            {"id": classification_id}
        )
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

class UserClearance(Base):
    __tablename__ = "user_clearances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    classification_id = Column(UUID(as_uuid=True), ForeignKey("classifications.id"))
    granted_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def has_clearance(cls, db: AsyncSession, user_id: str, classification_id: str):
        result = await db.execute(
            text("""
                SELECT id FROM user_clearances 
                WHERE user_id = :user_id AND classification_id = :classification_id
                LIMIT 1
            """),
            {"user_id": user_id, "classification_id": classification_id}
        )
        return result.first() is not None

    @classmethod
    async def get_user_clearances(cls, db: AsyncSession, user_id: str):
        result = await db.execute(
            text("""
                SELECT c.* FROM classifications c
                JOIN user_clearances uc ON c.id = uc.classification_id
                WHERE uc.user_id = :user_id
                ORDER BY c.level
            """),
            {"user_id": user_id}
        )
        rows = result.fetchall()
        return [Classification(**row._asdict()) for row in rows]

    @classmethod
    async def get_user_max_level(cls, db: AsyncSession, user_id: str):
        result = await db.execute(
            text("""
                SELECT MAX(c.level) as max_level 
                FROM classifications c
                JOIN user_clearances uc ON c.id = uc.classification_id
                WHERE uc.user_id = :user_id
            """),
            {"user_id": user_id}
        )
        row = result.first()
        return row.max_level if row and row.max_level else 0

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
    thumbnail_url = Column(String(500))
    status = Column(String(20), default="uploaded")
    is_private = Column(Boolean, default=False)
    tags = Column(ARRAY(String))
    views_count = Column(Integer, default=0)
    transcoding_progress = Column(Integer, default=0)  # 0-100%
    classification = Column(String(20), default="public")  # public, internal, confidential, restricted
    classification_id = Column(UUID(as_uuid=True), ForeignKey("classifications.id"))
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
                INSERT INTO videos (id, title, description, user_id, channel_id, duration, resolution, bitrate, file_size, minio_key, hls_playlist_url, status, is_private, tags, classification, created_at, updated_at)
                VALUES (:id, :title, :description, :user_id, :channel_id, :duration, :resolution, :bitrate, :file_size, :minio_key, :hls_playlist_url, :status, :is_private, :tags, :classification, :created_at, :updated_at)
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
                "classification": kwargs.get('classification', 'public'),
                "created_at": kwargs.get('created_at', datetime.utcnow()),
                "updated_at": kwargs.get('updated_at', datetime.utcnow())
            }
        )
        await db.commit()
        return await cls.get_by_id(db, video_id_str)

    @classmethod
    async def get_by_id(cls, db: AsyncSession, video_id: str):
        # Convert to string and clean up
        video_id_str = str(video_id).strip()
        
        # Try direct lookup - PostgreSQL will handle UUID conversion
        result = await db.execute(
            text("SELECT * FROM videos WHERE id::text = :id"),
            {"id": video_id_str}
        )
        row = result.first()
        if row:
            return cls(**row._asdict())
        
        # Try without hyphens if the ID has them
        no_hyphens = video_id_str.replace('-', '')
        if len(no_hyphens) == 32:
            # Format as UUID with hyphens
            formatted = f"{no_hyphens[:8]}-{no_hyphens[8:12]}-{no_hyphens[12:16]}-{no_hyphens[16:20]}-{no_hyphens[20:]}"
            result = await db.execute(
                text("SELECT * FROM videos WHERE id::text = :id"),
                {"id": formatted}
            )
            row = result.first()
            if row:
                return cls(**row._asdict())
        
        return None

    @classmethod
    async def get_all(cls, db: AsyncSession, skip: int = 0, limit: int = 10, user_id: str = None, channel_id: str = None):
        # Only show ready videos that are processed and available for viewing
        if channel_id:
            # Show all videos for channel (including restricted for owner)
            query = """
                SELECT * FROM videos
                WHERE channel_id = :channel_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """
            result = await db.execute(text(query), {"channel_id": channel_id, "limit": limit, "skip": skip})
        elif user_id:
            # For authenticated users, show their own videos (any status, any classification) +
            # public ready videos + restricted videos they have access to
            query = """
                SELECT * FROM videos
                WHERE (user_id = :user_id)
                   OR (is_private = false AND status = 'ready' AND (classification IS NULL OR classification != 'restricted'))
                   OR (classification = 'restricted' AND status = 'ready' AND id IN (
                       SELECT video_id FROM video_user_access WHERE user_id = :user_id
                   ))
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """
            result = await db.execute(text(query), {"user_id": user_id, "limit": limit, "skip": skip})
        else:
            # For anonymous users, show only public ready videos (not restricted)
            query = """
                SELECT * FROM videos
                WHERE is_private = false AND status = 'ready' AND (classification IS NULL OR classification != 'restricted')
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

        for field in ['duration', 'resolution', 'bitrate', 'hls_playlist_url', 'status', 'channel_id', 'transcoding_progress', 'classification_id']:
            if field in kwargs:
                update_fields.append(f"{field} = :{field}")
                params[field] = kwargs[field]

        if update_fields:
            update_fields.append("updated_at = NOW()")
            query = f"UPDATE videos SET {', '.join(update_fields)} WHERE id = :id"
            await db.execute(text(query), params)
            await db.commit()

class VideoLike(Base):
    __tablename__ = "video_likes"
    __table_args__ = (UniqueConstraint("video_id", "user_id", name="uq_video_likes_video_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class VideoView(Base):
    __tablename__ = "video_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    session_id = Column(String(255), nullable=True)
    watched_duration = Column(Interval, nullable=True)
    viewed_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class VideoUserAccess(Base):
    __tablename__ = "video_user_access"
    __table_args__ = (
        UniqueConstraint("video_id", "user_id", name="uq_video_user_access_video_user"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    granted_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    granted_by = Column(UUID(as_uuid=True))

    @classmethod
    async def grant_access(cls, db: AsyncSession, video_id: str, user_id: str, granted_by: str):
        """Grant access to a specific user for a video"""
        if await cls.check_access(db, video_id, user_id):
            return True
        try:
            await db.execute(
                text("""
                    INSERT INTO video_user_access (id, video_id, user_id, granted_at, granted_by)
                    VALUES (gen_random_uuid(), CAST(:video_id AS uuid), CAST(:user_id AS uuid), NOW(), CAST(:granted_by AS uuid))
                """),
                {"video_id": video_id, "user_id": user_id, "granted_by": granted_by},
            )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error("Failed to grant access: %s", e)
            return False

    @classmethod
    async def revoke_access(cls, db: AsyncSession, video_id: str, user_id: str):
        """Revoke access from a user for a video"""
        await db.execute(
            text("DELETE FROM video_user_access WHERE video_id = :video_id AND user_id = :user_id"),
            {"video_id": video_id, "user_id": user_id}
        )
        await db.commit()

    @classmethod
    async def check_access(cls, db: AsyncSession, video_id: str, user_id: str) -> bool:
        """Check if user has access to the video"""
        result = await db.execute(
            text("SELECT id FROM video_user_access WHERE video_id = :video_id AND user_id = :user_id LIMIT 1"),
            {"video_id": video_id, "user_id": user_id}
        )
        return result.first() is not None

    @classmethod
    async def get_allowed_users(cls, db: AsyncSession, video_id: str):
        """Get list of users with access to the video"""
        result = await db.execute(
            text("SELECT user_id, granted_at FROM video_user_access WHERE video_id = :video_id"),
            {"video_id": video_id}
        )
        rows = result.fetchall()
        return [{"user_id": str(row.user_id), "granted_at": row.granted_at} for row in rows]

    @classmethod
    async def get_access_video_ids_for_user(
        cls, db: AsyncSession, video_ids: list[str], user_id: str
    ) -> set[str]:
        """video_id, на которые у user_id есть явный доступ (batch)."""
        if not video_ids:
            return set()
        result = await db.execute(
            text(
                """
                SELECT video_id::text FROM video_user_access
                WHERE video_id = ANY(CAST(:video_ids AS uuid[]))
                  AND user_id = CAST(:user_id AS uuid)
                """
            ),
            {"video_ids": list({str(v) for v in video_ids}), "user_id": str(user_id)},
        )
        return {row[0] for row in result.fetchall()}

    @classmethod
    async def get_share_counts(cls, db: AsyncSession, video_ids: list[str]) -> dict[str, int]:
        """Число пользователей с доступом к каждому video_id (batch)."""
        if not video_ids:
            return {}
        result = await db.execute(
            text(
                """
                SELECT video_id::text, COUNT(*)::int AS cnt
                FROM video_user_access
                WHERE video_id = ANY(CAST(:video_ids AS uuid[]))
                GROUP BY video_id
                """
            ),
            {"video_ids": list({str(v) for v in video_ids})},
        )
        return {row[0]: row[1] for row in result.fetchall()}

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
