"""Auth module schemas for request and response validation."""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


# ======================== OTP Request/Response Schemas ========================

class SendOTPRequest(BaseModel):
    """Request schema for sending OTP.
    
    Users can send OTP via email or phone number.
    """
    email: Optional[EmailStr] = Field(None, description="Email address to send OTP")
    phone: Optional[str] = Field(None, description="Phone number to send OTP (international format)")
    otp_type: str = Field("email", description="Type of OTP: 'email' or 'sms'")
    
    @validator('otp_type')
    def validate_otp_type(cls, v):
        if v not in ['email', 'sms']:
            raise ValueError("otp_type must be 'email' or 'sms'")
        return v
    
    @validator('email', 'phone', pre=True, always=True)
    def validate_identifier(cls, v, values):
        """Ensure either email or phone is provided."""
        # This validator is called for each field
        if 'email' in values:
            email = values.get('email')
            phone = v if (hasattr(cls, '__fields__') and 'phone' in str(cls)) else values.get('phone')
            if not email and not phone:
                raise ValueError("Either email or phone must be provided")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "phone": None,
                "otp_type": "email"
            }
        }


class SendOTPResponse(BaseModel):
    """Response schema for sending OTP."""
    success: bool = Field(..., description="Whether OTP was sent successfully")
    message: str = Field(..., description="Response message")
    identifier: str = Field(..., description="Masked identifier (email or phone)")
    expires_in_seconds: int = Field(..., description="OTP expiration time in seconds")
    otp_type: str = Field(..., description="Type of OTP sent")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "OTP sent successfully to your email",
                "identifier": "us**@example.com",
                "expires_in_seconds": 120,
                "otp_type": "email"
            }
        }


class VerifyOTPRequest(BaseModel):
    """Request schema for verifying OTP."""
    email: Optional[EmailStr] = Field(None, description="Email used for OTP")
    phone: Optional[str] = Field(None, description="Phone used for OTP")
    otp: str = Field(..., min_length=4, max_length=10, description="OTP code to verify")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "phone": None,
                "otp": "123456"
            }
        }


class AuthTokenResponse(BaseModel):
    """Response schema for authentication token."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    user: dict = Field(..., description="User information with role")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_verified": True,
                    "role": {
                        "role_id": "role-uuid",
                        "role_name": "user",
                        "description": "Regular user"
                    }
                }
            }
        }


class VerifyOTPResponse(BaseModel):
    """Response schema for OTP verification."""
    success: bool = Field(..., description="Whether OTP verification was successful")
    message: str = Field(..., description="Response message")
    auth_token: Optional[AuthTokenResponse] = Field(None, description="Authentication token on success")
    remaining_attempts: Optional[int] = Field(None, description="Remaining OTP attempts on failure")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "OTP verified successfully",
                "auth_token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "user": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "user@example.com",
                        "full_name": "John Doe",
                        "is_verified": True,
                        "role": {
                            "role_id": "role-uuid",
                            "role_name": "user"
                        }
                    }
                },
                "remaining_attempts": None
            }
        }


class ResendOTPRequest(BaseModel):
    """Request schema for resending OTP."""
    email: Optional[EmailStr] = Field(None, description="Email to resend OTP")
    phone: Optional[str] = Field(None, description="Phone to resend OTP")
    otp_type: str = Field("email", description="Type of OTP: 'email' or 'sms'")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "phone": None,
                "otp_type": "email"
            }
        }


class ResendOTPResponse(BaseModel):
    """Response schema for resend OTP."""
    success: bool = Field(..., description="Whether OTP was resent successfully")
    message: str = Field(..., description="Response message")
    identifier: Optional[str] = Field(None, description="Masked identifier")
    expires_in_seconds: Optional[int] = Field(None, description="OTP expiration time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "OTP resent successfully",
                "identifier": "us**@example.com",
                "expires_in_seconds": 120
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token."""
    refresh_token: str = Field(..., description="Refresh token")
    
    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshTokenResponse(BaseModel):
    """Response schema for refreshing token."""
    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New or same refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


# ======================== User-related Schemas ========================

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating user."""
    pass


class RoleResponse(BaseModel):
    """Schema for role in responses."""
    role_id: str
    role_name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    role: Optional[RoleResponse] = None
    
    class Config:
        from_attributes = True


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


class UsersListResponse(BaseModel):
    """Schema for users list response."""
    success: bool
    message: str
    users: list
    total: int
    skip: int
    limit: int


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


class UserLoginResponse(UserResponse):
    """Schema for user login response."""
    auth_token: Optional[AuthTokenResponse] = None


# ======================== Error Response Schema ========================

class ErrorResponse(BaseModel):
    """Generic error response schema."""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "Invalid OTP",
                "error_code": "INVALID_OTP",
                "details": {
                    "remaining_attempts": 2
                }
            }
        }
