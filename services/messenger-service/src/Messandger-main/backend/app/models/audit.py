import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from app.types import GUID

from app.database import Base


class AuditLog(Base):
    """Журнал аудита: фиксирует значимые действия пользователей и системы."""
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    actor_id = Column(GUID, nullable=True)
    actor_email = Column(String(255))           # дублируем на случай удаления пользователя
    action = Column(String(80), nullable=False, index=True)  # login, logout, login_failed, message_send, message_delete, file_upload, admin_block, admin_unblock, password_change, backup_create, db_integrity_fail и т.п.
    object_type = Column(String(50))            # message, user, chat, file, system
    object_id = Column(String(80))
    ip_address = Column(String(64))
    user_agent = Column(String(300))
    status = Column(String(20), default="success")  # success, failed, warning
    details = Column(Text)                      # JSON
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class SystemMetric(Base):
    """Снимок системных метрик для построения графиков."""
    __tablename__ = "system_metrics"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    metric = Column(String(60), nullable=False, index=True)   # http_5xx, http_4xx, ws_active, login_failed, request_total
    value = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
