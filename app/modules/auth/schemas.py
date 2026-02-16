"""Auth module schemas with Pydantic models."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


class UserLoginSchema(BaseModel):
    """User login request schema."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password")


class UserRegisterSchema(BaseModel):
    """User registration request schema."""
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    password: str = Field(..., min_length=6, description="Password")


class TokenResponseSchema(BaseModel):
    """Token response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class RoleSchema(BaseModel):
    """Role schema."""
    role_id: str = Field(..., description="Role ID")
    role_name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    is_active: bool = Field(default=True, description="Is role active")


class PermissionSchema(BaseModel):
    """Permission schema."""
    permission_id: str = Field(..., description="Permission ID")
    permission_name: str = Field(..., description="Permission name")
    resource: str = Field(..., description="Resource name")
    action: str = Field(..., description="Action name")
    description: Optional[str] = Field(None, description="Permission description")


class UserResponseSchema(BaseModel):
    """User response schema."""
    id: str = Field(..., description="User ID")
    full_name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(default=True, description="Is user active")
    is_verified: bool = Field(default=False, description="Is user verified")
    role_name: Optional[str] = Field(None, description="User role name")


class UserDetailSchema(UserResponseSchema):
    """Detailed user schema with additional info."""
    created_at: Optional[str] = Field(None, description="User creation date")
    updated_at: Optional[str] = Field(None, description="User last update date")
    last_login: Optional[str] = Field(None, description="Last login date")


class ChangePasswordSchema(BaseModel):
    """Change password request schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., min_length=6, description="Confirm new password")


class UserPermissionsSchema(BaseModel):
    """User permissions schema."""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    role: Optional[RoleSchema] = Field(None, description="User role")
    permissions: List[PermissionSchema] = Field(default_factory=list, description="User permissions")
