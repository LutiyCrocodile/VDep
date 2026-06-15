from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    user = "user"
    engineer = "engineer"
    admin = "admin"


class PositionPriority(str, enum.Enum):
    vip = "vip"
    high = "high"
    medium = "medium"
    low = "low"


class Position(Base):
    """Должности сотрудников ДГИ с приоритетом."""
    __tablename__ = "positions"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="low", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)  # Для сортировки по приоритету

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TicketStatus(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    waiting_user = "waiting_user"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"
    vip = "vip"


class User(Base):
    """Локальный профиль support-сервиса: id = UUID из auth-service."""
    __tablename__ = "support_profiles"
    __table_args__ = {"schema": "support"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    position: Mapped[str | None] = mapped_column(String(120), nullable=True)  # Оставляем для обратной совместимости
    position_id: Mapped[int | None] = mapped_column(ForeignKey("support.positions.id"), nullable=True, index=True)
    internal_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    office: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    needs_approval: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tickets_created = relationship("Ticket", back_populates="created_by", foreign_keys="Ticket.created_by_id")
    tickets_assigned = relationship("Ticket", back_populates="assigned_to", foreign_keys="Ticket.assigned_to_id")
    position_obj = relationship("Position")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="new", index=True)

    priority: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        index=True,
    )

    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support.support_profiles.id"), index=True)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("support.support_profiles.id"), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="tickets_created")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="tickets_assigned")

    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    events = relationship("TicketEvent", back_populates="ticket", cascade="all, delete-orphan")


class TicketEvent(Base):
    __tablename__ = "ticket_events"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support.tickets.id"), index=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("support.support_profiles.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50))  # status_change, assigned, resolution, etc.
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="events")
    author = relationship("User")


class TicketComment(Base):
    __tablename__ = "ticket_comments"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support.tickets.id"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support.support_profiles.id"), index=True)
    body: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support.tickets.id"), index=True)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support.support_profiles.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket")
    uploaded_by = relationship("User")


class EquipmentCategory(str, enum.Enum):
    monoblock = "monoblock"
    printer = "printer"
    consumable = "consumable"


class ConsumableType(str, enum.Enum):
    cartridge = "cartridge"
    peripheral = "peripheral"
    cable = "cable"
    accessory = "accessory"


class EquipmentStatus(str, enum.Enum):
    in_stock = "in_stock"
    assigned = "assigned"
    retired = "retired"


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(20), default="monoblock", index=True)
    consumable_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    name: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), default="in_stock")
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("support.support_profiles.id"), nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_warehouse: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    assigned_to_user = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support.support_profiles.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    broadcast_id: Mapped[int | None] = mapped_column(ForeignKey("support.broadcasts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    broadcast = relationship("Broadcast")


class Broadcast(Base):
    __tablename__ = "broadcasts"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support.support_profiles.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    author = relationship("User")
    notifications = relationship("Notification", back_populates="broadcast", cascade="all, delete-orphan")


class KbCategory(str, enum.Enum):
    faq = "faq"              # Частые вопросы
    guide = "guide"          # Инструкции
    policy = "policy"        # Политики/регламенты
    software = "software"    # ПО и установщики
    template = "template"    # Шаблоны документов


class KbArticle(Base):
    """FAQ / инструкции для пользователей и сотрудников."""
    __tablename__ = "kb_articles"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)           # markdown-контент
    category: Mapped[str] = mapped_column(String(20), default="faq", index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support.support_profiles.id"), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    author = relationship("User")
    files = relationship("KbFile", back_populates="article", cascade="all, delete-orphan")


class KbFile(Base):
    """Файлы базы знаний — установщики, документы, шаблоны."""
    __tablename__ = "kb_files"
    __table_args__ = {"schema": "support"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("support.kb_articles.id"), nullable=True, index=True)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support.support_profiles.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    article = relationship("KbArticle", back_populates="files")
    uploaded_by = relationship("User")
