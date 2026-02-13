"""Auth module routes for OTP-based authentication with services."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import re

from app.core.database import SessionLocal
from app.core.security import (
    create_access_token, 
    create_refresh_token,
    create_token_pair,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from app.modules.auth.models import User, OTPToken
from app.modules.auth.services import (
    OTPService, 
    OTPType, 
    UserAuthService,
    UserService
)
from app.modules.auth import schemas


# Create router instance
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}}
)


# Dependency to get database session
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def mask_identifier(identifier: str) -> str:
    """Mask email or phone for display."""
    if "@" in identifier:  # Email
        parts = identifier.split("@")
        prefix = parts[0]
        if len(prefix) > 2:
            masked = prefix[:2] + "*" * (len(prefix) - 2) + "@" + parts[1]
        else:
            masked = "*" * len(prefix) + "@" + parts[1]
        return masked
    else:  # Phone
        if len(identifier) >= 4:
            return "*" * (len(identifier) - 4) + identifier[-4:]
        return "*" * len(identifier)



# ======================== SEND OTP ENDPOINT ========================

@router.post(
    "/send-otp",
    response_model=schemas.SendOTPResponse,
    summary="Send OTP to user's email or phone",
    responses={
        200: {"description": "OTP sent successfully"},
        400: {"description": "Bad request - invalid email or phone format"},
        429: {"description": "Too many requests - rate limited"},
    }
)
async def send_otp(
    request: schemas.SendOTPRequest,
    db: Session = Depends(get_db)
):
    """Send OTP - Business logic delegated to services."""
    try:
        if request.email:
            identifier = request.email
            identifier_type = "email"
            otp_type = OTPType.EMAIL
        elif request.phone:
            if not re.match(r'^\+?1?\d{9,15}$', request.phone.replace("-", "").replace(" ", "")):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number format")
            identifier = request.phone
            identifier_type = "phone"
            otp_type = OTPType.SMS
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either email or phone must be provided")

        user_result = UserService.get_user_by_email(db, identifier) if identifier_type == "email" else UserService.get_user_by_phone(db, identifier)
        
        if not user_result["success"]:
            create_result = UserService.create_user(
                db,
                email=identifier if identifier_type == "email" else f"user_{identifier}@placeholder.com",
                full_name=identifier.split("@")[0] if identifier_type == "email" else f"User_{identifier}",
                phone=identifier if identifier_type == "phone" else None
            )
            if not create_result["success"]:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=create_result["message"])
            user = db.query(User).filter(
                User.email == (identifier if identifier_type == "email" else None),
                User.phone == (identifier if identifier_type == "phone" else None)
            ).first()
        else:
            user = db.query(User).filter(
                User.email == identifier if identifier_type == "email" else User.phone == identifier
            ).first()

        otp = OTPService.generate_numeric_otp()
        otp_metadata = OTPService.store_otp(identifier=identifier, otp=otp, otp_type=otp_type, expiry_minutes=2)

        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(minutes=2)
        otp_token = OTPToken(
            user_id=user.id,
            identifier=identifier,
            otp_type=identifier_type,
            is_verified=False,
            verification_attempts=0,
            expires_at=expires_at
        )
        db.add(otp_token)
        db.commit()

        print(f"\n{'='*50}\nOTP for {identifier}: {otp}\nExpires in: 2 minutes\n{'='*50}\n")

        return schemas.SendOTPResponse(
            success=True,
            message=f"OTP sent successfully to {identifier_type}",
            identifier=mask_identifier(identifier),
            expires_in_seconds=otp_metadata["ttl_seconds"],
            otp_type=identifier_type
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP")


# ======================== VERIFY OTP ENDPOINT ========================

@router.post(
    "/verify-otp",
    response_model=schemas.VerifyOTPResponse,
    summary="Verify OTP and get authentication tokens",
    responses={
        200: {"description": "OTP verified successfully, tokens returned"},
        400: {"description": "Invalid OTP or bad request"},
        401: {"description": "OTP verification failed"},
        429: {"description": "Too many attempts"},
    }
)
async def verify_otp(
    request: schemas.VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    """Verify OTP and return JWT tokens (access + refresh) - Business logic delegated to services."""
    try:
        if request.email:
            identifier = request.email
            identifier_type = "email"
        elif request.phone:
            identifier = request.phone
            identifier_type = "phone"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either email or phone must be provided")

        is_valid, message = OTPService.validate_otp(identifier=identifier, otp=request.otp)

        if not is_valid:
            otp_info = OTPService.get_otp_info(identifier)
            remaining_attempts = 3 - otp_info.get("attempts", 0) if otp_info else None
            otp_token = db.query(OTPToken).filter(OTPToken.identifier == identifier, OTPToken.is_verified == False).order_by(OTPToken.created_at.desc()).first()
            if otp_token:
                otp_token.verification_attempts += 1
                db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=schemas.VerifyOTPResponse(success=False, message=message, remaining_attempts=remaining_attempts).dict())

        user = db.query(User).filter(User.email == identifier if identifier_type == "email" else User.phone == identifier).first()

        if not user:
            create_result = UserService.create_user(
                db,
                email=identifier if identifier_type == "email" else f"user_{identifier}@placeholder.com",
                full_name=identifier.split("@")[0] if identifier_type == "email" else f"User_{identifier}",
                phone=identifier if identifier_type == "phone" else None
            )
            if not create_result["success"]:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=create_result["message"])
            user = db.query(User).filter(User.email == identifier if identifier_type == "email" else User.phone == identifier).first()

        otp_token = db.query(OTPToken).filter(OTPToken.identifier == identifier, OTPToken.is_verified == False).order_by(OTPToken.created_at.desc()).first()
        if otp_token:
            otp_token.is_verified = True
            otp_token.verified_at = datetime.utcnow()
            db.commit()

        UserService.update_user(db, user.id, is_verified=True)
        user.last_login = datetime.utcnow()
        db.commit()

        token_data = {"sub": user.id, "email": user.email, "full_name": user.full_name, "is_verified": user.is_verified}
        tokens = create_token_pair(token_data)
        user_data = UserAuthService.format_user_response(user)
        
        auth_token = schemas.AuthTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_data
        )

        OTPService.clear_otp(identifier)

        return schemas.VerifyOTPResponse(success=True, message="OTP verified successfully", auth_token=auth_token, remaining_attempts=None)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying OTP: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify OTP")


# ======================== RESEND OTP ENDPOINT ========================

@router.post(
    "/resend-otp",
    response_model=schemas.ResendOTPResponse,
    summary="Resend OTP with validation checks",
    responses={
        200: {"description": "OTP resent successfully"},
        400: {"description": "Bad request"},
        401: {"description": "Invalid request or too many attempts"},
    }
)
async def resend_otp(
    request: schemas.ResendOTPRequest,
    db: Session = Depends(get_db)
):
    """Resend OTP with checks - Business logic delegated to UserService."""
    try:
        if request.email:
            identifier = request.email
            identifier_type = "email"
        elif request.phone:
            if not re.match(r'^\+?1?\d{9,15}$', request.phone.replace("-", "").replace(" ", "")):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number format")
            identifier = request.phone
            identifier_type = "phone"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either email or phone must be provided")

        success, message, otp = UserService.resend_otp(db, identifier, identifier_type)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED if "attempts" in message.lower() else status.HTTP_400_BAD_REQUEST,
                detail=schemas.ResendOTPResponse(success=False, message=message).dict()
            )

        print(f"\n{'='*50}\nOTP for {identifier}: {otp}\nExpires in: 2 minutes\n{'='*50}\n")

        return schemas.ResendOTPResponse(success=True, message="OTP resent successfully", identifier=mask_identifier(identifier), expires_in_seconds=120)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resending OTP: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to resend OTP")


# ======================== REFRESH TOKEN ENDPOINT ========================

@router.post(
    "/refresh-token",
    response_model=schemas.RefreshTokenResponse,
    summary="Refresh access token using refresh token",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid or expired refresh token"},
    }
)
async def refresh_token_endpoint(
    request: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(request.refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user_id = payload.get("sub")
        user_result = UserService.get_user_by_id(db, user_id)
        
        if not user_result["success"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        token_data = {"sub": user_id, "email": payload.get("email"), "full_name": payload.get("full_name"), "is_verified": payload.get("is_verified")}
        tokens = create_token_pair(token_data)

        return schemas.RefreshTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error refreshing token: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token")


# ======================== USER CRUD ENDPOINTS ========================

@router.post(
    "/users",
    response_model=schemas.UserCreatedResponse,
    summary="Create a new user",
    responses={
        200: {"description": "User created successfully"},
        400: {"description": "User already exists or invalid data"},
    }
)
async def create_user(
    request: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Create a new user - Business logic delegated to UserService."""
    result = UserService.create_user(db, email=request.email, full_name=request.full_name, phone=request.phone)
    
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
    
    return schemas.UserCreatedResponse(success=result["success"], message=result["message"], user=result["user"])


@router.get(
    "/users/{user_id}",
    response_model=schemas.UserResponse,
    summary="Get user by ID",
    responses={
        200: {"description": "User retrieved successfully"},
        404: {"description": "User not found"},
    }
)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user by ID - Business logic delegated to UserService."""
    result = UserService.get_user_by_id(db, user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])
    
    return result["user"]


@router.get(
    "/users",
    response_model=schemas.UsersListResponse,
    summary="Get all users with pagination",
    responses={
        200: {"description": "Users retrieved successfully"},
    }
)
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all users with pagination - Business logic delegated to UserService."""
    result = UserService.get_all_users(db, skip=skip, limit=limit)
    
    return schemas.UsersListResponse(
        success=result["success"],
        message=result["message"],
        users=result["users"],
        total=result["total"],
        skip=result["skip"],
        limit=result["limit"]
    )


@router.put(
    "/users/{user_id}",
    response_model=schemas.UserUpdatedResponse,
    summary="Update user",
    responses={
        200: {"description": "User updated successfully"},
        404: {"description": "User not found"},
    }
)
async def update_user(
    user_id: str,
    request: schemas.UserUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update user information - Business logic delegated to UserService."""
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    result = UserService.update_user(db, user_id, **update_data)
    
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])
    
    return schemas.UserUpdatedResponse(success=result["success"], message=result["message"], user=result["user"])


@router.delete(
    "/users/{user_id}",
    response_model=schemas.UserDeletedResponse,
    summary="Delete user",
    responses={
        200: {"description": "User deleted successfully"},
        404: {"description": "User not found"},
    }
)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Delete a user - Business logic delegated to UserService."""
    result = UserService.delete_user(db, user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])
    
    return schemas.UserDeletedResponse(success=result["success"], message=result["message"])


# ======================== UTILITY ENDPOINTS (TESTING) ========================

@router.get(
    "/otp-status/{identifier}",
    summary="Check OTP status (for testing only)",
    responses={
        200: {"description": "OTP status returned"},
        404: {"description": "OTP not found"},
    }
)
async def get_otp_status(identifier: str):
    """Get OTP status for an identifier (for testing/debugging)."""
    try:
        otp_info = OTPService.get_otp_info(identifier)
        
        if not otp_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OTP not found")
        
        return {"success": True, "data": otp_info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error retrieving OTP status: {str(e)}")


@router.get(
    "/redis-stats",
    summary="Get Redis OTP statistics (for testing only)",
    responses={
        200: {"description": "Redis stats returned"},
    }
)
async def get_redis_stats():
    """Get Redis OTP storage statistics (for testing/monitoring)."""
    try:
        stats = OTPService.get_redis_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error retrieving Redis stats: {str(e)}")



