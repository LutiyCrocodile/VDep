import logging
from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger("db")

metadata = MetaData(schema=settings.DB_SCHEMA if "sqlite" not in settings.DATABASE_URL else None)


def _build_engine():
    url = settings.DATABASE_URL
    connect_args = {}

    if "sqlite" in url:
        eng = create_async_engine(url, echo=False, connect_args=connect_args)
        if settings.DB_ENCRYPTION_KEY:
            @event.listens_for(eng.sync_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, _):
                try:
                    cur = dbapi_connection.cursor()
                    cur.execute(f"PRAGMA key='{settings.DB_ENCRYPTION_KEY}';")
                    cur.execute("PRAGMA cipher_compatibility=4;")
                    cur.close()
                    logger.info("SQLCipher: ключ применён")
                except Exception as e:
                    logger.warning("SQLCipher недоступен (%s) — БД работает без шифрования", e)
        return eng

    if settings.DB_REQUIRE_TLS and "postgresql" in url:
        if "sslmode" not in url and "ssl=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}ssl=require"
        connect_args["ssl"] = True
    return create_async_engine(url, echo=False, pool_size=20, max_overflow=10, connect_args=connect_args)


engine = _build_engine()
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    metadata = metadata


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        if "postgresql" in settings.DATABASE_URL:
            from sqlalchemy import text
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.DB_SCHEMA}"'))
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_columns(conn)


async def _ensure_columns(conn):
    if "sqlite" not in settings.DATABASE_URL:
        return
    from sqlalchemy import text

    async def has_column(table: str, col: str) -> bool:
        res = await conn.execute(text(f"PRAGMA table_info({table})"))
        return any(r[1] == col for r in res.fetchall())

    async def add_column(table: str, definition: str):
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))

    try:
        if not await has_column("messages", "allow_download"):
            await add_column("messages", "allow_download BOOLEAN DEFAULT 1")
    except Exception as e:
        print(f"[migrations] messages.allow_download: {e}")
