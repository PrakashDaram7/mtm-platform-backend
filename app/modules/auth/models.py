"""
Authentication & Authorization Models — Aligned with MTM PRD Section 3.

Roles (PRD 3.1):
  1. Public Visitor      — no login (not stored)
  2. Member              — registered + paid individual
  3. Family Member       — linked to a Member profile
  4. Volunteer           — member or non-member, applied + approved
  5. Committee Member    — elevated member with committee duties
  6. Admin (Super Admin) — full system access
  7. Finance Admin       — payments, receipts, donation reports
  8. Event Manager       — events + volunteers management
  9. Moderator           — forum moderation, content flags
"""

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Date, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class Role(Base):
    """Role model — PRD Section 3.1.

    Maps to the 8 login-capable roles defined in the PRD.
    Public Visitor has no login and is not stored here.
    """
    __tablename__ = "roles"

    role_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", back_populates="role")


class Permission(Base):
    """Permission model — PRD Section 3.2.

    Defines granular resource-action permissions per role.
    """
    __tablename__ = "permissions"

    permission_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    permission_name = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=True)
    resource = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    role_id = Column(CHAR(36), ForeignKey("roles.role_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    role = relationship("Role", back_populates="permissions")


class User(Base):
    """User/Member model — PRD Section 5.2.

    Profile fields aligned with PRD 5.2.3:
      - Full name, Phone, Email, Address, DOB, Occupation
      - Preferred language (English/Telugu)
      - Consent toggles (WhatsApp, email, emergency broadcasts)
    """
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # --- Core Identity (PRD 5.2.3) ---
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)

    # --- Extended Profile (PRD 5.2.3) ---
    address = Column(Text, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    occupation = Column(String(100), nullable=True)
    preferred_language = Column(String(20), default="English")  # English or Telugu

    # --- Consent Toggles (PRD 5.2.3) ---
    consent_whatsapp = Column(Boolean, default=False)
    consent_email = Column(Boolean, default=True)
    consent_emergency = Column(Boolean, default=False)

    # --- Account Status ---
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # --- Role Assignment ---
    role_id = Column(CHAR(36), ForeignKey("roles.role_id"), nullable=True)
    role = relationship("Role", back_populates="users")

    # --- Timestamps ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    otps = relationship("OTP", back_populates="user")
    family_members = relationship("FamilyMember", back_populates="primary_member", foreign_keys="FamilyMember.member_id")


class FamilyMember(Base):
    """Family Member linking — PRD Section 5.2.4.

    Basic Phase 1: name + relation + phone.
    Extensible for Phase 2 (blood group, etc).
    """
    __tablename__ = "family_members"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    relation = Column(String(50), nullable=False)  # e.g. spouse, child, parent, sibling
    phone = Column(String(20), nullable=True)
    email = Column(String(150), nullable=True)

    # Extensible fields for Phase 2
    date_of_birth = Column(Date, nullable=True)
    blood_group = Column(String(5), nullable=True)  # Phase 2 field, kept extensible

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    primary_member = relationship("User", back_populates="family_members", foreign_keys=[member_id])


class OTP(Base):
    """OTP model for email/phone verification."""
    __tablename__ = "otps"

    otp_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    otp_type = Column(String(10), nullable=False)  # 'email' or 'phone'
    otp_code = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_used = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="otps")


class AuditLog(Base):
    """Audit Log — PRD Section 3.3 (Mandatory).

    Must log:
      - Membership changes (create/renew/expire/override)
      - Payment events (success/fail/refund)
      - Admin content edits (pages/announcements)
      - AI-generated official documents that are sent/exported
      - Emergency blood request broadcasts
    """
    __tablename__ = "audit_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g. 'membership.create', 'payment.success'
    resource_type = Column(String(100), nullable=True, index=True)  # e.g. 'membership', 'payment', 'event'
    resource_id = Column(String(100), nullable=True)  # ID of the affected resource
    details = Column(JSON, nullable=True)  # Additional context as JSON
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
