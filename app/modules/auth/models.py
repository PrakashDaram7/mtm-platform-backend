"""Auth module models placeholder.

TODO:
- Implement this file as part of assigned development tasks.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Foreignkey,relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base



class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)
    role_id = Column(Foreignkey("role.role_id"))
    role=relationship("Role",backpopulates="User")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

