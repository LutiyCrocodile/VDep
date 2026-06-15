import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from app.types import GUID
from sqlalchemy.orm import relationship

from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    short_name = Column(String(100))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    divisions = relationship("Division", back_populates="department")
    users = relationship("User", back_populates="department")


class Division(Base):
    __tablename__ = "divisions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    department_id = Column(GUID, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(300), nullable=False)
    short_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    department = relationship("Department", back_populates="divisions")
    users = relationship("User", back_populates="division")


class User(Base):
    """Локальный профиль мессенджера: id = UUID из auth-service."""

    __tablename__ = "messenger_profiles"

    id = Column(GUID, primary_key=True)
    email = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    patronymic = Column(String(100))
    avatar_url = Column(String(500))
    avatar_visibility = Column(String(20), default="all")
    avatar_visibility_list = Column(Text)
    phone = Column(String(20))
    department_id = Column(GUID, ForeignKey("departments.id", ondelete="SET NULL"))
    division_id = Column(GUID, ForeignKey("divisions.id", ondelete="SET NULL"))
    position = Column(String(200))
    role = Column(String(30), default="user")
    status = Column(String(20), default="offline")
    last_seen = Column(DateTime(timezone=True), default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_frozen = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department", back_populates="users")
    division = relationship("Division", back_populates="users")

    @property
    def is_admin_role(self):
        return self.role in ("super_admin", "admin")

    @property
    def is_head_role(self):
        return self.role in ("head", "deputy_head")

    @property
    def password_expired(self):
        return False


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    patronymic = Column(String(100))
    email = Column(String(255), nullable=False)
    phone = Column(String(20))
    department_id = Column(GUID, ForeignKey("departments.id"))
    division_id = Column(GUID, ForeignKey("divisions.id"))
    position = Column(String(200))
    reason = Column(Text)
    status = Column(String(20), default="pending")
    # Removed FK to messenger_profiles - store UUID directly without constraint
    reviewed_by = Column(GUID)
    review_comment = Column(Text)
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ProfileChangeRequest(Base):
    __tablename__ = "profile_change_requests"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    user_id = Column(GUID, nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String(200))
    new_value = Column(String(200), nullable=False)
    status = Column(String(20), default="pending")
    # Removed FK to messenger_profiles - store UUID directly without constraint
    reviewed_by = Column(GUID)
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
