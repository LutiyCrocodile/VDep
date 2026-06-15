from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.session import engine


async def _has_column(table_name: str, column_name: str) -> bool:
    from app.core.config import DATABASE_URL, DB_SCHEMA
    is_postgres = "postgresql" in DATABASE_URL
    schema_name = DB_SCHEMA if is_postgres else "DATABASE()"

    if is_postgres:
        sql = text(
            f"""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = '{schema_name}'
              AND table_name = :table
              AND column_name = :col
            LIMIT 1
            """
        )
    else:
        sql = text(
            f"""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = :table
              AND column_name = :col
            LIMIT 1
            """
        )
    async with engine.connect() as conn:
        result = await conn.execute(sql, {"table": table_name, "col": column_name})
        return result.first() is not None


async def _has_table(table_name: str) -> bool:
    from app.core.config import DATABASE_URL, DB_SCHEMA
    is_postgres = "postgresql" in DATABASE_URL
    schema_name = DB_SCHEMA if is_postgres else "DATABASE()"

    if is_postgres:
        sql = text(
            f"""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = '{schema_name}'
              AND table_name = :table
            LIMIT 1
            """
        )
    else:
        sql = text(
            f"""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = :table
            LIMIT 1
            """
        )
    async with engine.connect() as conn:
        result = await conn.execute(sql, {"table": table_name})
        return result.first() is not None


async def ensure_schema() -> None:
    from app.core.config import DATABASE_URL, DB_SCHEMA
    is_postgres = "postgresql" in DATABASE_URL
    schema_prefix = f"{DB_SCHEMA}." if is_postgres else ""

    # PostgreSQL uses SERIAL (which includes INT), MySQL uses AUTO_INCREMENT
    auto_increment = "SERIAL" if is_postgres else "INT NOT NULL AUTO_INCREMENT"

    # PostgreSQL uses BOOLEAN for flags, MySQL uses TINYINT(1)
    bool_type = "BOOLEAN" if is_postgres else "TINYINT(1)"
    bool_default = "FALSE" if is_postgres else "0"

    # PostgreSQL uses UUID for user IDs, MySQL uses CHAR(36)
    uuid_type = "UUID" if is_postgres else "CHAR(36)"

    # PostgreSQL uses TIMESTAMP, MySQL uses DATETIME
    datetime_type = "TIMESTAMP" if is_postgres else "DATETIME"

    index_creates: list[str] = []

    async with engine.begin() as conn:
        # Create support_profiles table (User model)
        if not await _has_table("support_profiles"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}support_profiles (
                        id {uuid_type} NOT NULL PRIMARY KEY,
                        username VARCHAR(50) NOT NULL UNIQUE,
                        full_name VARCHAR(150) NULL,
                        position VARCHAR(120) NULL,
                        internal_number VARCHAR(20) NULL,
                        office VARCHAR(20) NULL,
                        avatar_path VARCHAR(255) NULL,
                        role VARCHAR(20) NOT NULL DEFAULT 'user',
                        is_active {bool_type} NOT NULL DEFAULT TRUE,
                        needs_approval {bool_type} NOT NULL DEFAULT FALSE,
                        created_at {datetime_type} NULL
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_support_profiles_username ON {DB_SCHEMA}.support_profiles (username)")

        # Create tickets table
        if not await _has_table("tickets"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}tickets (
                        id {auto_increment},
                        title VARCHAR(200) NOT NULL,
                        description TEXT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'new',
                        priority VARCHAR(20) NOT NULL DEFAULT 'normal',
                        resolution TEXT NULL,
                        created_by_id {uuid_type} NOT NULL,
                        assigned_to_id {uuid_type} NULL,
                        created_at {datetime_type} NULL,
                        updated_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_tickets_status ON {DB_SCHEMA}.tickets (status)")
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_tickets_created_by_id ON {DB_SCHEMA}.tickets (created_by_id)")
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_tickets_assigned_to_id ON {DB_SCHEMA}.tickets (assigned_to_id)")

        # Create ticket_events table
        if not await _has_table("ticket_events"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}ticket_events (
                        id {auto_increment},
                        ticket_id INT NOT NULL,
                        author_id {uuid_type} NULL,
                        event_type VARCHAR(50) NOT NULL,
                        old_value TEXT NULL,
                        new_value TEXT NULL,
                        created_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_ticket_events_ticket_id ON {DB_SCHEMA}.ticket_events (ticket_id)")

        # Create ticket_attachments table
        if not await _has_table("ticket_attachments"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}ticket_attachments (
                        id {auto_increment},
                        ticket_id INT NOT NULL,
                        uploaded_by_id {uuid_type} NOT NULL,
                        file_path VARCHAR(255) NOT NULL,
                        created_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_ticket_attachments_ticket_id ON {DB_SCHEMA}.ticket_attachments (ticket_id)")
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_ticket_attachments_uploaded_by_id ON {DB_SCHEMA}.ticket_attachments (uploaded_by_id)")

        # Create ticket_comments table
        if not await _has_table("ticket_comments"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}ticket_comments (
                        id {auto_increment},
                        ticket_id INT NOT NULL,
                        author_id {uuid_type} NOT NULL,
                        body TEXT NOT NULL,
                        created_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_ticket_comments_ticket_id ON {DB_SCHEMA}.ticket_comments (ticket_id)")

        # Create equipment table
        if not await _has_table("equipment"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}equipment (
                        id {auto_increment},
                        category VARCHAR(20) NOT NULL DEFAULT 'monoblock',
                        consumable_type VARCHAR(20) NULL,
                        model VARCHAR(150) NULL,
                        serial_number VARCHAR(80) NULL UNIQUE,
                        name VARCHAR(150) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'in_stock',
                        assigned_to_user_id {uuid_type} NULL,
                        location VARCHAR(20) NULL,
                        is_warehouse {bool_type} NOT NULL DEFAULT FALSE,
                        notes TEXT NULL,
                        created_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_equipment_category ON {DB_SCHEMA}.equipment (category)")
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_equipment_assigned_to_user_id ON {DB_SCHEMA}.equipment (assigned_to_user_id)")

        # Create kb_articles table
        if not await _has_table("kb_articles"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}kb_articles (
                        id {auto_increment},
                        title VARCHAR(200) NOT NULL,
                        body TEXT NOT NULL,
                        category VARCHAR(20) NOT NULL DEFAULT 'faq',
                        is_published {bool_type} NOT NULL DEFAULT TRUE,
                        author_id {uuid_type} NOT NULL,
                        updated_at {datetime_type} NULL,
                        created_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_kb_articles_category ON {DB_SCHEMA}.kb_articles (category)")
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_kb_articles_author_id ON {DB_SCHEMA}.kb_articles (author_id)")

        # Create kb_files table
        if not await _has_table("kb_files"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}kb_files (
                        id {auto_increment},
                        article_id INT NULL,
                        uploaded_by_id {uuid_type} NOT NULL,
                        file_path VARCHAR(255) NOT NULL,
                        original_name VARCHAR(255) NOT NULL,
                        file_size INT NOT NULL DEFAULT 0,
                        created_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_kb_files_article_id ON {DB_SCHEMA}.kb_files (article_id)")
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_kb_files_uploaded_by_id ON {DB_SCHEMA}.kb_files (uploaded_by_id)")

        # Create broadcasts table
        if not await _has_table("broadcasts"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}broadcasts (
                        id {auto_increment},
                        author_id {uuid_type} NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        body TEXT NOT NULL,
                        created_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_broadcasts_author_id ON {DB_SCHEMA}.broadcasts (author_id)")

        # Create notifications table
        if not await _has_table("notifications"):
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {schema_prefix}notifications (
                        id {auto_increment},
                        user_id {uuid_type} NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        body TEXT NULL,
                        is_read {bool_type} NOT NULL DEFAULT FALSE,
                        broadcast_id INT NULL,
                        created_at {datetime_type} NULL,
                        PRIMARY KEY (id)
                    )
                    """
                )
            )
            if is_postgres:
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON {DB_SCHEMA}.notifications (user_id)")
                index_creates.append(f"CREATE INDEX IF NOT EXISTS ix_notifications_broadcast_id ON {DB_SCHEMA}.notifications (broadcast_id)")

        # Create indexes separately for PostgreSQL
        for idx_stmt in index_creates:
            try:
                await conn.execute(text(idx_stmt))
            except Exception:
                pass

        # Add foreign keys separately (only if tables exist)
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}ticket_events ADD CONSTRAINT fk_ticket_events_ticket_id FOREIGN KEY(ticket_id) REFERENCES {DB_SCHEMA}.tickets (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}ticket_events ADD CONSTRAINT fk_ticket_events_author_id FOREIGN KEY(author_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE SET NULL"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}ticket_attachments ADD CONSTRAINT fk_ticket_attachments_ticket_id FOREIGN KEY(ticket_id) REFERENCES {DB_SCHEMA}.tickets (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}ticket_attachments ADD CONSTRAINT fk_ticket_attachments_uploaded_by_id FOREIGN KEY(uploaded_by_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}ticket_comments ADD CONSTRAINT fk_ticket_comments_ticket_id FOREIGN KEY(ticket_id) REFERENCES {DB_SCHEMA}.tickets (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}ticket_comments ADD CONSTRAINT fk_ticket_comments_author_id FOREIGN KEY(author_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}tickets ADD CONSTRAINT fk_tickets_created_by_id FOREIGN KEY(created_by_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}tickets ADD CONSTRAINT fk_tickets_assigned_to_id FOREIGN KEY(assigned_to_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE SET NULL"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}equipment ADD CONSTRAINT fk_equipment_assigned_to_user_id FOREIGN KEY(assigned_to_user_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE SET NULL"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}kb_articles ADD CONSTRAINT fk_kb_articles_author_id FOREIGN KEY(author_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}kb_files ADD CONSTRAINT fk_kb_files_article_id FOREIGN KEY(article_id) REFERENCES {DB_SCHEMA}.kb_articles (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}kb_files ADD CONSTRAINT fk_kb_files_uploaded_by_id FOREIGN KEY(uploaded_by_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}broadcasts ADD CONSTRAINT fk_broadcasts_author_id FOREIGN KEY(author_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}notifications ADD CONSTRAINT fk_notifications_user_id FOREIGN KEY(user_id) REFERENCES {DB_SCHEMA}.support_profiles (id) ON DELETE CASCADE"))
        except Exception:
            pass
        try:
            await conn.execute(text(f"ALTER TABLE {schema_prefix}notifications ADD CONSTRAINT fk_notifications_broadcast_id FOREIGN KEY(broadcast_id) REFERENCES {DB_SCHEMA}.broadcasts (id) ON DELETE SET NULL"))
        except Exception:
            pass
