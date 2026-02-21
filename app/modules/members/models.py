"""
Members module models — Sprint 2: Full Membership Management (PRD 5.3)

Models:
  - MembershipPlan     : Admin-managed plans (Annual, Lifetime, etc.)
  - Membership         : Per-member record with PRD-required fields
  - MembershipNote     : Admin notes per membership (audit trail)
  - AppSettings        : Platform-level settings (auto_approve_membership, etc.)
"""

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Float, Date, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# 1. MEMBERSHIP PLAN  (Admin-managed)
# ─────────────────────────────────────────────────────────────────────────────
class MembershipPlan(Base):
    """Available membership plans — created & managed by Admin only (PRD 5.3.1)."""
    __tablename__ = "membership_plans"

    id               = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name             = Column(String(100), nullable=False, unique=True)
    description      = Column(Text, nullable=True)
    membership_type  = Column(String(50), default="individual")  # individual | family | other
    price            = Column(Float, nullable=False)
    currency         = Column(String(10), default="MUR")
    duration_months  = Column(Integer, nullable=True)       # NULL = lifetime
    is_lifetime      = Column(Boolean, default=False)
    features         = Column(Text, nullable=True)           # JSON array string
    is_active        = Column(Boolean, default=True)
    sort_order       = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    memberships = relationship("Membership", back_populates="plan")


# ─────────────────────────────────────────────────────────────────────────────
# 2. MEMBERSHIP  (Core PRD 5.3.1)
# ─────────────────────────────────────────────────────────────────────────────
class Membership(Base):
    """
    Core membership record per PRD Section 5.3.1.

    Status values:
      pending   → application submitted, awaiting admin approval
      active    → approved + paid, within expiry
      expired   → past expiry date
      blocked   → admin manually blocked (with reason)
      rejected  → admin rejected application
    """
    __tablename__ = "memberships"

    id                = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id           = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id           = Column(CHAR(36), ForeignKey("membership_plans.id"), nullable=True, index=True)

    # Human-readable membership number (e.g. MTM-2026-00001)
    membership_number = Column(String(50), unique=True, nullable=True, index=True)

    # Type mirrors plan but stored separately for migrations
    membership_type   = Column(String(50), default="individual")  # individual | family | other

    # Status (PRD 5.3.1)
    status            = Column(String(20), default="pending", index=True)

    # Dates (PRD 5.3.1)
    start_date        = Column(DateTime(timezone=True), nullable=True)
    expiry_date       = Column(DateTime(timezone=True), nullable=True)

    # Financial
    amount_paid       = Column(Float, default=0.0)
    payment_id        = Column(CHAR(36), nullable=True)  # link to payments table

    # Admin fields
    admin_notes       = Column(Text, nullable=True)
    rejection_reason  = Column(Text, nullable=True)
    block_reason      = Column(Text, nullable=True)
    approved_by       = Column(CHAR(36), ForeignKey("users.id"), nullable=True)
    approved_at       = Column(DateTime(timezone=True), nullable=True)

    # Renewal history stored as JSON list of {date, plan, amount, extended_to}
    renewal_history   = Column(JSON, nullable=True, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user     = relationship("User", foreign_keys=[user_id], back_populates="membership")
    plan     = relationship("MembershipPlan", back_populates="memberships")
    approver = relationship("User", foreign_keys=[approved_by])


# ─────────────────────────────────────────────────────────────────────────────
# 3. APP SETTINGS  (Platform-level toggles, stored in DB)
# ─────────────────────────────────────────────────────────────────────────────
class AppSettings(Base):
    """
    Key-value platform settings store.
    admin can manage via /admin/settings API.

    Relevant keys for Sprint 2:
      auto_approve_membership  → "true" / "false"
    """
    __tablename__ = "app_settings"

    id          = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key         = Column(String(100), unique=True, nullable=False, index=True)
    value       = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_by  = Column(CHAR(36), ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY: Keep MemberSubscription so existing FKs don't break (deprecated)
# ─────────────────────────────────────────────────────────────────────────────
class MemberSubscription(Base):
    """Legacy subscription model — kept for backward compat. Use Membership instead."""
    __tablename__ = "member_subscriptions"

    id          = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id     = Column(CHAR(36), ForeignKey("membership_plans.id"), nullable=False, index=True)
    status      = Column(String(20), default="active", index=True)
    start_date  = Column(DateTime(timezone=True), server_default=func.now())
    end_date    = Column(DateTime(timezone=True), nullable=True)
    payment_id  = Column(CHAR(36), nullable=True)
    amount_paid = Column(Float, default=0.0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    plan = relationship("MembershipPlan")
