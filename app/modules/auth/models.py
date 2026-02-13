
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey,  Integer, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class Role(Base):
    """Role model for authentication and authorization.
    
    Defines different roles (admin, user, moderator, etc.) with associated permissions.
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
    """Permission model for defining role-based access control."""
    __tablename__ = "permissions"

    permission_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    permission_name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    resource = Column(String(100), nullable=False, index=True)  # e.g., 'users', 'events', 'payments'
    action = Column(String(50), nullable=False)  # e.g., 'create', 'read', 'update', 'delete'
    role_id = Column(CHAR(36), ForeignKey("roles.role_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="permissions")


class User(Base):
    """User model for authentication and user management.
    
    Stores user account information, authentication credentials, and profile data.
    """
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)

    last_login = Column(DateTime(timezone=True), nullable=True)

    role_id = Column(CHAR(36), ForeignKey("roles.role_id"), nullable=True)
    role = relationship("Role", back_populates="users")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    otp_tokens = relationship("OTPToken", back_populates="user")


class OTPToken(Base):
    """OTP Token model for tracking OTP usage during login.
    
    Stores OTP logs for audit trail and rate limiting.
    """
    __tablename__ = "otp_tokens"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    identifier = Column(String(150), nullable=False, index=True)  # email or phone
    otp_type = Column(String(20), nullable=False)  # 'email' or 'sms'
    is_verified = Column(Boolean, default=False, index=True)
    verification_attempts = Column(Integer, default=0)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="otp_tokens")
    

