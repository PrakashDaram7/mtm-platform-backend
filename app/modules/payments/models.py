"""Payments module models."""

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class Payment(Base):
    """Payment records."""
    __tablename__ = "payments"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(20), default="pending", index=True)  # pending, completed, failed, refunded
    payment_type = Column(String(50), nullable=False)  # membership, event, donation
    payment_method = Column(String(50), nullable=True)  # upi, card, netbanking
    transaction_id = Column(String(200), nullable=True, unique=True)
    reference_id = Column(CHAR(36), nullable=True)  # event_id or plan_id
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
