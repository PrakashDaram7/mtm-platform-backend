"""Members module models — Membership plans and subscriptions."""

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class MembershipPlan(Base):
    """Available membership plans."""
    __tablename__ = "membership_plans"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    duration_months = Column(Integer, nullable=True)  # NULL = lifetime
    is_lifetime = Column(Boolean, default=False)
    features = Column(Text, nullable=True)  # JSON string of features
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subscriptions = relationship("MemberSubscription", back_populates="plan")


class MemberSubscription(Base):
    """User membership subscriptions."""
    __tablename__ = "member_subscriptions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(CHAR(36), ForeignKey("membership_plans.id"), nullable=False, index=True)
    status = Column(String(20), default="active", index=True)  # active, expired, cancelled
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)  # NULL = lifetime
    payment_id = Column(CHAR(36), nullable=True)
    amount_paid = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    plan = relationship("MembershipPlan", back_populates="subscriptions")
