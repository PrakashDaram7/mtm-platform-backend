"""Admin module schemas for request and response validation."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ======================== Role Schemas ========================

class RoleSchema(BaseModel):
    """Role schema."""
    role_id: str = Field(..., description="Role ID")
    role_name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    is_active: bool = Field(default=True, description="Is role active")


class RoleResponse(BaseModel):
    """Schema for role in responses."""
    role_id: str
    role_name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


# ======================== Permission Schemas ========================

class PermissionSchema(BaseModel):
    """Permission schema."""
    permission_id: str = Field(..., description="Permission ID")
    permission_name: str = Field(..., description="Permission name")
    resource: str = Field(..., description="Resource name")
    action: str = Field(..., description="Action name")
    description: Optional[str] = Field(None, description="Permission description")


# ======================== User Management Schemas ========================

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating user."""
    pass


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    role: Optional[RoleResponse] = None
    
    class Config:
        from_attributes = True


class UserDetailSchema(UserResponse):
    """Detailed user schema with additional info."""
    updated_at: Optional[datetime] = Field(None, description="User last update date")
    last_login: Optional[datetime] = Field(None, description="Last login date")


class UserResponseSchema(BaseModel):
    """User response schema."""
    id: str = Field(..., description="User ID")
    full_name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(default=True, description="Is user active")
    is_verified: bool = Field(default=False, description="Is user verified")
    role_name: Optional[str] = Field(None, description="User role name")


class UserUpdateRequest(BaseModel):
    """Schema for updating user."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    
    class Config:
        schema_extra = {
            "example": {
                "full_name": "John Doe Updated",
                "phone": "+1234567890",
                "is_active": True
            }
        }


class UserCreatedResponse(BaseModel):
    """Schema for user creation response."""
    success: bool
    message: str
    user: Optional[UserResponse] = None


class UserUpdatedResponse(BaseModel):
    """Schema for user update response."""
    success: bool
    message: str
    user: Optional[UserResponse] = None


class UserDeletedResponse(BaseModel):
    """Schema for user deletion response."""
    success: bool
    message: str


class UsersListResponse(BaseModel):
    """Schema for users list response."""
    success: bool
    message: str
    users: list
    total: int
    skip: int
    limit: int


class UserPermissionsSchema(BaseModel):
    """User permissions schema."""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    role: Optional[RoleSchema] = Field(None, description="User role")
    permissions: List[PermissionSchema] = Field(default_factory=list, description="User permissions")
