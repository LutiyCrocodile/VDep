import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from app.types import GUID
from sqlalchemy.orm import relationship

from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    user_id = Column(GUID, nullable=False)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    contact_id = Column(GUID, nullable=False)
    is_blocked = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
