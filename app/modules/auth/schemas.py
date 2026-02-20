"""Auth module schemas for request and response validation.

OTP-only authentication — no password fields anywhere.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


# ======================== Token Schemas ========================

class TokenResponseSchema(BaseModel):
    """Token response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


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
    """Request schema for verifying OTP.
    
    No password required — authentication is entirely OTP-based.
    For signup: provide full_name along with email and otp.
    For signin: provide only email and otp.
    """
    email: Optional[EmailStr] = Field(None, description="Email used for OTP")
    phone: Optional[str] = Field(None, description="Phone used for OTP")
    otp: str = Field(..., min_length=4, max_length=10, description="OTP code to verify")
    full_name: Optional[str] = Field(None, description="Full name for new user signup")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "phone": None,
                "otp": "123456",
                "full_name": None
            }
        }


class VerifyOTPResponse(BaseModel):
    """Response schema for OTP verification."""
    success: bool = Field(..., description="Whether OTP verification was successful")
    message: str = Field(..., description="Response message")
    user_id: Optional[str] = Field(None, description="User ID")
    email: Optional[str] = Field(None, description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    role: Optional[str] = Field(None, description="User role")
    access_token: Optional[str] = Field(None, description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "OTP verified successfully",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "Ravi Kumar",
                "role": "member",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
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


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token."""
    refresh_token: str = Field(..., description="Refresh token")
    
    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


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
