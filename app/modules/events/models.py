"""Events module models — Event and EventRegistration."""

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class EventType(str, enum.Enum):
    CULTURAL = "cultural"
    EDUCATION = "education"
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    SOCIAL = "social"
    SPORTS = "sports"
    OTHER = "other"


class Event(Base):
    """Event model for community events management."""
    __tablename__ = "events"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    event_type = Column(String(50), default="other")
    status = Column(String(20), default="draft", index=True)

    # Date & Location
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    venue = Column(String(200), nullable=True)
    is_online = Column(Boolean, default=False)
    meeting_link = Column(String(500), nullable=True)

    # Capacity & Pricing
    max_capacity = Column(Integer, nullable=True)
    fee = Column(Float, default=0.0)
    is_free = Column(Boolean, default=True)
    members_only = Column(Boolean, default=False)

    # Image
    image_url = Column(String(500), nullable=True)

    # Organizer
    organizer_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    organizer = relationship("User", foreign_keys=[organizer_id])

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    registrations = relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan")


class RegistrationStatus(str, enum.Enum):
    REGISTERED = "registered"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    ATTENDED = "attended"


class EventRegistration(Base):
    """Registration model linking users to events."""
    __tablename__ = "event_registrations"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(CHAR(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="registered", index=True)
    payment_status = Column(String(20), default="pending")  # pending, paid, refunded
    amount_paid = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    event = relationship("Event", back_populates="registrations")
    user = relationship("User", foreign_keys=[user_id])
