import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from app.types import GUID

from app.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    user_id = Column(GUID, nullable=False)
    token_hash = Column(String(255), nullable=False)
    device_info = Column(String(500))
    ip_address = Column(String(45))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
