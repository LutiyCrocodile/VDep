from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID, text
from typing import AsyncGenerator, List, Optional
import uuid
from datetime import datetime
from .config import settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)


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
    archived_video_id = Column(UUID(as_uuid=True))
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    visibility = Column(String(32), default="dgi_employees")
    mediamtx_path = Column(String(255))
    recording_dir = Column(String(512))
    archive_status = Column(String(32))
    archive_error = Column(String)
    save_recording = Column(Boolean, default=True, nullable=False)

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        stream_id = uuid.uuid4()
        visibility = kwargs.get("visibility", "dgi_employees")
        is_private = visibility == "private"
        await db.execute(
            text(
                """
                INSERT INTO streams (
                    id, title, description, user_id, rtmp_key, hls_url, is_live,
                    start_time, end_time, archived_video_id, is_private, created_at,
                    visibility, mediamtx_path, recording_dir, save_recording
                )
                VALUES (
                    :id, :title, :description, :user_id, :rtmp_key, :hls_url, :is_live,
                    :start_time, :end_time, :archived_video_id, :is_private, :created_at,
                    :visibility, :mediamtx_path, :recording_dir, :save_recording
                )
                """
            ),
            {
                "id": stream_id,
                "title": kwargs["title"],
                "description": kwargs.get("description"),
                "user_id": kwargs["user_id"],
                "rtmp_key": kwargs["rtmp_key"],
                "hls_url": kwargs.get("hls_url"),
                "is_live": kwargs.get("is_live", False),
                "start_time": kwargs.get("start_time"),
                "end_time": kwargs.get("end_time"),
                "archived_video_id": kwargs.get("archived_video_id"),
                "is_private": is_private,
                "created_at": kwargs.get("created_at", datetime.utcnow()),
                "visibility": visibility,
                "mediamtx_path": kwargs.get("mediamtx_path"),
                "recording_dir": kwargs.get("recording_dir"),
                "save_recording": kwargs.get("save_recording", True),
            },
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
    async def get_all(cls, db: AsyncSession, user_id: Optional[str] = None):
        if user_id:
            query = """
                SELECT * FROM streams
                WHERE user_id = CAST(:user_id AS uuid)
                ORDER BY created_at DESC
            """
            result = await db.execute(text(query), {"user_id": user_id})
        else:
            query = """
                SELECT * FROM streams
                WHERE COALESCE(visibility, 'dgi_employees') != 'private'
                ORDER BY created_at DESC
            """
            result = await db.execute(text(query))

        rows = result.fetchall()
        return [cls(**row._asdict()) for row in rows]

    @classmethod
    async def get_latest_for_owner(cls, db: AsyncSession, owner_id: str):
        result = await db.execute(
            text(
                """
                SELECT * FROM streams
                WHERE user_id = CAST(:uid AS uuid)
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"uid": owner_id},
        )
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def get_open_session_for_owner(cls, db: AsyncSession, owner_id: str):
        """Текущая подготовка/эфир (ещё не завершён)."""
        result = await db.execute(
            text(
                """
                SELECT * FROM streams
                WHERE user_id = CAST(:uid AS uuid) AND end_time IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"uid": owner_id},
        )
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def get_streams_for_rtmp_reconcile(cls, db: AsyncSession):
        """Открытые эфиры, которые могли остаться без RTMP (webhook MediaMTX недоступен)."""
        result = await db.execute(
            text(
                """
                SELECT * FROM streams
                WHERE end_time IS NULL AND (is_live = true OR start_time IS NOT NULL)
                """
            )
        )
        return [cls(**row._asdict()) for row in result.fetchall()]

    @classmethod
    async def get_recent_ended_for_owner(cls, db: AsyncSession, owner_id: str, limit: int = 8):
        """Недавно завершённые эфиры (для фоновой архивации на go-live)."""
        result = await db.execute(
            text(
                """
                SELECT * FROM streams
                WHERE user_id = CAST(:uid AS uuid) AND end_time IS NOT NULL
                  AND COALESCE(save_recording, true) = true
                ORDER BY end_time DESC NULLS LAST, created_at DESC
                LIMIT :lim
                """
            ),
            {"uid": owner_id, "lim": limit},
        )
        return [cls(**row._asdict()) for row in result.fetchall()]

    @classmethod
    async def update_status(
        cls,
        db: AsyncSession,
        stream_id: str,
        is_live: bool = None,
        start_time: datetime = None,
        end_time: datetime = None,
        hls_url: str = None,
        archived_video_id: str = None,
        recording_dir: str = None,
        archive_status: str = None,
        archive_error: str = None,
    ):
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

        if recording_dir is not None:
            update_fields.append("recording_dir = :recording_dir")
            params["recording_dir"] = recording_dir

        if archive_status is not None:
            update_fields.append("archive_status = :archive_status")
            params["archive_status"] = archive_status

        if archive_error is not None:
            update_fields.append("archive_error = :archive_error")
            params["archive_error"] = archive_error

        if update_fields:
            query = f"UPDATE streams SET {', '.join(update_fields)} WHERE id = :id"
            await db.execute(text(query), params)
            await db.commit()

    @classmethod
    async def reset_archive(cls, db: AsyncSession, stream_id: str):
        """Сброс зависшей/отменённой архивации — можно создать новый эфир."""
        await db.execute(
            text(
                """
                UPDATE streams
                SET archive_status = NULL,
                    archive_error = NULL,
                    archived_video_id = NULL
                WHERE id = :id
                """
            ),
            {"id": stream_id},
        )
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
        result = await db.execute(
            text("SELECT * FROM streams WHERE is_live = true ORDER BY start_time DESC NULLS LAST")
        )
        rows = result.fetchall()
        return [cls(**row._asdict()) for row in rows]


async def replace_stream_viewers(db: AsyncSession, stream_id: str, user_ids: List[str]):
    await db.execute(
        text("DELETE FROM stream_viewers WHERE stream_id = CAST(:sid AS uuid)"),
        {"sid": stream_id},
    )
    for uid in user_ids:
        if not uid:
            continue
        await db.execute(
            text(
                """
                INSERT INTO stream_viewers (stream_id, user_id)
                VALUES (CAST(:sid AS uuid), CAST(:uid AS uuid))
                ON CONFLICT (stream_id, user_id) DO NOTHING
                """
            ),
            {"sid": stream_id, "uid": uid.strip()},
        )
    await db.commit()


async def is_stream_viewer(db: AsyncSession, stream_id: str, user_id: str) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1 FROM stream_viewers
            WHERE stream_id = CAST(:sid AS uuid) AND user_id = CAST(:uid AS uuid)
            LIMIT 1
            """
        ),
        {"sid": stream_id, "uid": user_id},
    )
    return result.first() is not None


async def list_stream_viewer_ids(db: AsyncSession, stream_id: str) -> List[str]:
    result = await db.execute(
        text(
            "SELECT user_id::text FROM stream_viewers WHERE stream_id = CAST(:sid AS uuid)"
        ),
        {"sid": stream_id},
    )
    return [str(row[0]) for row in result.fetchall()]


async def get_channel_for_owner(db: AsyncSession, owner_id: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (channel_id, channel_handle) for stream owner."""
    result = await db.execute(
        text(
            "SELECT id::text, handle FROM channels WHERE owner_id = CAST(:oid AS uuid) LIMIT 1"
        ),
        {"oid": owner_id},
    )
    row = result.first()
    if not row:
        return None, None
    return str(row[0]), str(row[1]) if row[1] else None


async def get_stream_likes_count(db: AsyncSession, stream_id: str) -> int:
    result = await db.execute(
        text("SELECT COUNT(*) FROM stream_likes WHERE stream_id = CAST(:sid AS uuid)"),
        {"sid": stream_id},
    )
    return int(result.scalar() or 0)


async def user_liked_stream(db: AsyncSession, stream_id: str, user_id: str) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1 FROM stream_likes
            WHERE stream_id = CAST(:sid AS uuid) AND user_id = CAST(:uid AS uuid)
            LIMIT 1
            """
        ),
        {"sid": stream_id, "uid": user_id},
    )
    return result.first() is not None


async def add_stream_like(db: AsyncSession, stream_id: str, user_id: str) -> bool:
    if await user_liked_stream(db, stream_id, user_id):
        return False
    await db.execute(
        text(
            """
            INSERT INTO stream_likes (id, stream_id, user_id, created_at)
            VALUES (gen_random_uuid(), CAST(:sid AS uuid), CAST(:uid AS uuid), NOW())
            """
        ),
        {"sid": stream_id, "uid": user_id},
    )
    await db.commit()
    return True


async def remove_stream_like(db: AsyncSession, stream_id: str, user_id: str) -> bool:
    result = await db.execute(
        text(
            """
            DELETE FROM stream_likes
            WHERE stream_id = CAST(:sid AS uuid) AND user_id = CAST(:uid AS uuid)
            """
        ),
        {"sid": stream_id, "uid": user_id},
    )
    await db.commit()
    return result.rowcount > 0


async def get_video_likes_count(db: AsyncSession, video_id: str) -> int:
    result = await db.execute(
        text("SELECT COUNT(*) FROM video_likes WHERE video_id = CAST(:vid AS uuid)"),
        {"vid": video_id},
    )
    return int(result.scalar() or 0)


async def user_liked_video(db: AsyncSession, video_id: str, user_id: str) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1 FROM video_likes
            WHERE video_id = CAST(:vid AS uuid) AND user_id = CAST(:uid AS uuid)
            LIMIT 1
            """
        ),
        {"vid": video_id, "uid": user_id},
    )
    return result.first() is not None


async def transfer_stream_likes_to_video(db: AsyncSession, stream_id: str, video_id: str) -> int:
    """Копирует лайки эфира в video_likes (без дубликатов). Возвращает число перенесённых."""
    result = await db.execute(
        text(
            """
            INSERT INTO video_likes (id, video_id, user_id, created_at)
            SELECT gen_random_uuid(), CAST(:vid AS uuid), sl.user_id, sl.created_at
            FROM stream_likes sl
            WHERE sl.stream_id = CAST(:sid AS uuid)
            ON CONFLICT ON CONSTRAINT uq_video_likes_video_user DO NOTHING
            """
        ),
        {"sid": stream_id, "vid": video_id},
    )
    await db.commit()
    return result.rowcount or 0


engine = create_async_engine(settings.database_url, echo=False, future=True)

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
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS stream_viewers (
                    stream_id UUID NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
                    user_id UUID NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (stream_id, user_id)
                )
                """
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE streams ADD COLUMN IF NOT EXISTS visibility VARCHAR(32) NOT NULL DEFAULT 'dgi_employees'"
            )
        )
        await conn.execute(text("ALTER TABLE streams ADD COLUMN IF NOT EXISTS mediamtx_path VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE streams ADD COLUMN IF NOT EXISTS recording_dir VARCHAR(512)"))
        await conn.execute(text("ALTER TABLE streams ADD COLUMN IF NOT EXISTS archive_status VARCHAR(32)"))
        await conn.execute(text("ALTER TABLE streams ADD COLUMN IF NOT EXISTS archive_error TEXT"))
        await conn.execute(
            text(
                "ALTER TABLE streams ADD COLUMN IF NOT EXISTS save_recording BOOLEAN NOT NULL DEFAULT true"
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS stream_likes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    stream_id UUID NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
                    user_id UUID NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    CONSTRAINT uq_stream_likes_stream_user UNIQUE (stream_id, user_id)
                )
                """
            )
        )
