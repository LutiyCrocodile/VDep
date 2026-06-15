import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy import JSON
from app.types import GUID

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    user_id = Column(GUID, nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text)
    data = Column(JSON)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
