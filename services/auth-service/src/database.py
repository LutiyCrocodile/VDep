from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID, text
from typing import AsyncGenerator
import uuid
from datetime import datetime
from .config import settings

class Base(DeclarativeBase):
    pass

class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def get_by_name(cls, db: AsyncSession, name: str):
        result = await db.execute(text("SELECT * FROM roles WHERE name = :name"), {"name": name})
        row = result.first()
        if row:
            return cls(**row._asdict())
        return None

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        role_id = uuid.uuid4()
        await db.execute(
            text("""
                INSERT INTO roles (id, name, description)
                VALUES (:id, :name, :description)
            """),
            {
                "id": role_id,
                "name": kwargs['name'],
                "description": kwargs.get('description', '')
            }
        )
        await db.commit()
        return str(role_id)

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255))
    ldap_dn = Column(String(255))
    esia_id = Column(String(255))
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    async def get_by_username(cls, db: AsyncSession, username: str):
        result = await db.execute(text("SELECT u.*, r.name as role_name FROM users u LEFT JOIN roles r ON u.role_id = r.id WHERE u.username = :username"), {"username": username})
        row = result.first()
        if row:
            user_dict = row._asdict()
            user = cls(**{k: v for k, v in user_dict.items() if k != 'role_name'})
            user.role = Role(name=user_dict['role_name']) if user_dict['role_name'] else None
            return user
        return None

    @classmethod
    async def get_by_email(cls, db: AsyncSession, email: str):
        result = await db.execute(text("SELECT u.*, r.name as role_name FROM users u LEFT JOIN roles r ON u.role_id = r.id WHERE u.email = :email"), {"email": email})
        row = result.first()
        if row:
            user_dict = row._asdict()
            user = cls(**{k: v for k, v in user_dict.items() if k != 'role_name'})
            user.role = Role(name=user_dict['role_name']) if user_dict['role_name'] else None
            return user
        return None

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        user_id = uuid.uuid4()
        role_id = kwargs.get('role_id')
        await db.execute(
            text("""
                INSERT INTO users (id, username, email, password_hash, ldap_dn, esia_id, role_id, is_active)
                VALUES (:id, :username, :email, :password_hash, :ldap_dn, :esia_id, :role_id, :is_active)
            """),
            {
                "id": user_id,
                "username": kwargs['username'],
                "email": kwargs['email'],
                "password_hash": kwargs.get('password_hash'),
                "ldap_dn": kwargs.get('ldap_dn'),
                "esia_id": kwargs.get('esia_id'),
                "role_id": role_id,
                "is_active": kwargs.get('is_active', True)
            }
        )
        await db.commit()

        # Fetch the created user with role
        return await cls.get_by_username(db, kwargs['username'])

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
