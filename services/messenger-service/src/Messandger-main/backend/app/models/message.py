import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, BigInteger, Integer
from app.types import GUID
from sqlalchemy.orm import relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    chat_id = Column(GUID, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    sender_id = Column(GUID, nullable=False)
    content = Column(Text)
    message_type = Column(String(20), default="text")  # text, file, image, video, audio, voice, system, poll
    reply_to_id = Column(GUID, ForeignKey("messages.id", ondelete="SET NULL"))
    forwarded_from_id = Column(GUID, ForeignKey("messages.id", ondelete="SET NULL"))
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    allow_download = Column(Boolean, default=True)
    scheduled_at = Column(DateTime(timezone=True))
    is_scheduled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")
    # Removed sender relationship - User is queried separately (no FK)
    attachments = relationship("MessageAttachment", back_populates="message", lazy="selectin", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="message", lazy="selectin", cascade="all, delete-orphan")
    reply_to = relationship("Message", foreign_keys=[reply_to_id], remote_side="Message.id", lazy="selectin")
    poll = relationship("Poll", back_populates="message", uselist=False, lazy="selectin", cascade="all, delete-orphan")


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    message_id = Column(GUID, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(100), nullable=False)
    thumbnail_url = Column(String(500))
    width = Column(Integer)
    height = Column(Integer)
    duration = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    message = relationship("Message", back_populates="attachments")


class MessageReadStatus(Base):
    __tablename__ = "message_read_status"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    message_id = Column(GUID, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    user_id = Column(GUID, nullable=False)
    read_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    message_id = Column(GUID, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    user_id = Column(GUID, nullable=False)
    emoji = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    message = relationship("Message", back_populates="reactions")
    # Removed user relationship - User is queried separately (no FK)


class Poll(Base):
    __tablename__ = "polls"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    message_id = Column(GUID, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False)
    is_multiple_choice = Column(Boolean, default=False)
    closes_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    message = relationship("Message", back_populates="poll")
    options = relationship("PollOption", back_populates="poll", lazy="selectin", cascade="all, delete-orphan")


class PollOption(Base):
    __tablename__ = "poll_options"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    poll_id = Column(GUID, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    option_text = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)

    poll = relationship("Poll", back_populates="options")
    votes = relationship("PollVote", back_populates="option", lazy="selectin", cascade="all, delete-orphan")


class PollVote(Base):
    __tablename__ = "poll_votes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    poll_id = Column(GUID, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    option_id = Column(GUID, ForeignKey("poll_options.id", ondelete="CASCADE"), nullable=False)
    # Removed FK to messenger_profiles - store UUID directly without constraint
    user_id = Column(GUID, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    option = relationship("PollOption", back_populates="votes")
    # Removed user relationship - User is queried separately (no FK)
