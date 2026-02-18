"""Authentication routes with RBAC support."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import SessionLocal
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    verify_password,
    hash_password,
    get_current_user,
    get_db,
    get_user_from_db,
    TokenData,
    user_has_role,
    user_has_any_role,
)
from app.modules.auth.models import User, Role, Permission
from app.modules.auth.schemas import (
    UserLoginSchema,
    UserRegisterSchema,
    TokenResponseSchema,
    ChangePasswordSchema,
    SendOTPRequest,
    VerifyOTPRequest,
)
from app.modules.admin.schemas import (
    UserResponseSchema,
    UserDetailSchema,
)
from app.modules.auth.services import OTPService, OTPType
from app.core.email_service import EmailService

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}}
)


@router.post("/register", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegisterSchema, db: Session = Depends(get_db)) -> dict:
    """Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        Created user data with user role
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Get default 'user' role
    user_role = db.query(Role).filter(Role.role_name == "user").first()
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user role not found. Please initialize default roles."
        )
    
    # Trim and validate password
    password = user_data.password.strip() if user_data.password else user_data.password
    
    try:
        password_hash = hash_password(password)
    except ValueError as e:
        print(f"❌ Password validation error for {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Create new user
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=password_hash,
        role_id=user_role.role_id,
        is_active=True,
        is_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "full_name": new_user.full_name,
        "email": new_user.email,
        "phone": new_user.phone,
        "is_active": new_user.is_active,
        "is_verified": new_user.is_verified,
        "role_name": user_role.role_name
    }


@router.post("/login", response_model=TokenResponseSchema)
async def login(credentials: UserLoginSchema, db: Session = Depends(get_db)) -> dict:
    """Login user and return access/refresh tokens.
    
    Args:
        credentials: User login credentials (email and password)
        db: Database session
        
    Returns:
        Access and refresh tokens
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Get user roles
    roles = [user.role.role_name] if user.role else ["user"]
    
    # Create tokens
    access_token = create_access_token(user.id, user.email, roles)
    refresh_token = create_refresh_token(user.id, user.email)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=TokenResponseSchema)
async def refresh_token_endpoint(
    request: dict,
    db: Session = Depends(get_db)
) -> dict:
    """Refresh access token using refresh token.
    
    Args:
        request: Dictionary containing refresh_token
        db: Database session
        
    Returns:
        New access token and refresh token
    """
    from app.core.security import verify_token
    
    refresh_token = request.get("refresh_token") if isinstance(request, dict) else None
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required in request body"
        )
    
    try:
        payload = verify_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        user = get_user_from_db(user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        roles = [user.role.role_name] if user.role else ["user"]
        access_token = create_access_token(user_id, email, roles)
        refresh_token_new = create_refresh_token(user_id, email)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_new,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.get("/me", response_model=UserDetailSchema)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Get current authenticated user's information.
    
    Args:
        current_user: Current authenticated user token data
        db: Database session
        
    Returns:
        Current user details
    """
    user = get_user_from_db(current_user.user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role_name": user.role.role_name if user.role else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None
    }


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordSchema,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Change user password.
    
    Args:
        password_data: Current and new password
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    user = get_user_from_db(current_user.user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not verify_password(password_data.current_password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match"
        )
    
    # Trim and validate new password
    new_password = password_data.new_password.strip() if password_data.new_password else password_data.new_password
    
    try:
        password_hash = hash_password(new_password)
    except ValueError as e:
        print(f"❌ Password validation error for user {current_user.user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    user.password_hash = password_hash
    db.commit()
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }


# ==================== ROLE & ADMIN MANAGEMENT ROUTES ====================

@router.get("/admin-panel")
async def admin_panel(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Admin-only protected route - access control panel.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Admin panel data
    """
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_role(user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    return {
        "message": f"Welcome to admin panel, {user.full_name}",
        "role": user.role.role_name if user.role else None,
        "total_users": db.query(User).count(),
        "active_users": db.query(User).filter(User.is_active == True).count(),
        "total_roles": db.query(Role).count()
    }


@router.get("/moderator-panel")
async def moderator_panel(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Moderator-only protected route - moderation panel.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Moderator panel data
    """
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_any_role(user, ["admin", "moderator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Moderator role required."
        )
    
    return {
        "message": f"Welcome to moderator panel, {user.full_name}",
        "role": user.role.role_name if user.role else None,
        "status": "ready for moderation"
    }





# ==================== OTP ROUTES ====================

@router.post("/signup-send-otp")
async def signup_send_otp(request: SendOTPRequest, db: Session = Depends(get_db)) -> dict:
    """Send OTP for signup. Only for new users (email must not exist)."""
    email = request.email
    otp_type = request.otp_type

    # Require email for signup
    if not email:
        raise HTTPException(status_code=400, detail="Email is required for signup")
    
    if otp_type not in ["email", "sms"]:
        raise HTTPException(status_code=400, detail="otp_type must be 'email' or 'sms'")

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return {"success": False, "message": "Email already registered. Please sign in instead.", "account_exists": True}

    try:
        otp = OTPService.generate_numeric_otp()
        otp_metadata = OTPService.store_otp(
            identifier=email,
            otp=otp,
            otp_type=OTPType.EMAIL if otp_type == "email" else OTPType.SMS,
            expiry_minutes=5,
        )

        # Send OTP via email
        if otp_type == "email":
            email_sent = EmailService.send_otp_email(email, otp)
            if not email_sent:
                print(f"⚠️ Failed to send email. OTP for {email}: {otp}")
                return {"success": False, "message": "Failed to send OTP email. Please check your email configuration."}
            masked = email[:2] + "***" + email[-10:] if len(email) > 12 else email[:1] + "***" + email[-1:]
        else:
            return {"success": False, "message": "OTP via phone/SMS is not yet implemented. Please use email for signup."}

        print(f"✅ Signup OTP sent for {email}: {otp_metadata}")
        return {
            "success": True,
            "message": f"OTP sent to {masked}",
            "identifier": masked,
            "expires_in_seconds": otp_metadata["ttl_seconds"],
            "otp_type": otp_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")


@router.post("/send-otp")
async def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)) -> dict:
    """Send OTP via email or phone for verification. Only for existing users."""
    email = request.email
    phone = request.phone
    otp_type = request.otp_type

    # Require otp_type
    if otp_type not in ["email", "sms"]:
        raise HTTPException(status_code=400, detail="otp_type must be 'email' or 'sms'")

    # Check user existence and status
    user = None
    if otp_type == "email":
        if not email:
            raise HTTPException(status_code=400, detail="Email is required for email OTP")
        user = db.query(User).filter(User.email == email).first()
    elif otp_type == "sms":
        if not phone:
            raise HTTPException(status_code=400, detail="Phone is required for SMS OTP")
        user = db.query(User).filter(User.phone == phone).first()

    if not user:
        return {"success": False, "message": f"No account found for the provided {otp_type}. Please sign up first."}
    if not user.is_active:
        return {"success": False, "message": "Account is disabled. Please contact support."}

    # (Optional) If you want to block OTP for already verified users, add here
    # if user.is_verified:
    #     return {"success": False, "message": "Account already verified. Please login."}

    try:
        otp = OTPService.generate_numeric_otp()
        otp_metadata = OTPService.store_otp(
            identifier=email if otp_type == "email" else phone,
            otp=otp,
            otp_type=OTPType.EMAIL if otp_type == "email" else OTPType.SMS,
            expiry_minutes=5,
            phone=phone,
        )

        # Send OTP
        if otp_type == "email":
            email_sent = EmailService.send_otp_email(email, otp)
            if not email_sent:
                print(f"⚠️ Failed to send email. OTP for {email}: {otp}")
                return {"success": False, "message": "Failed to send OTP email. Please check your email configuration."}
            masked = email[:2] + "***" + email[-10:] if len(email) > 12 else email[:1] + "***" + email[-1:]
        else:
            # TODO: Implement SMS sending logic here
            # For now, respond as not implemented
            return {"success": False, "message": "OTP via phone/SMS is not yet implemented. Please use an email address to receive your OTP."}

        print(f"✅ OTP stored for {email or phone}: {otp_metadata}")
        return {
            "success": True,
            "message": f"OTP sent to {masked}",
            "identifier": masked,
            "expires_in_seconds": otp_metadata["ttl_seconds"],
            "otp_type": otp_type
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )


@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)) -> dict:
    """Verify OTP and authenticate user or create new user on signup.
    
    Args:
        request: VerifyOTPRequest with 'email', 'otp', optional 'full_name', 'password'
        db: Database session
        
    Returns:
        Tokens and user data after successful verification
    """
    email = request.email
    otp = request.otp
    full_name = request.full_name
    password = request.password
    
    if not all([email, otp]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and OTP are required"
        )
    
    # Trim password if provided
    if password:
        password = password.strip()
    
    try:
        # Validate OTP
        is_valid, message = OTPService.validate_otp(email, otp)
        
        if not is_valid:
            print(f"❌ OTP validation failed for {email}: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        print(f"✅ OTP validated successfully for {email}")
        
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            # User exists - this is a signin
            existing_user.is_verified = True
            db.commit()
            
            roles = [existing_user.role.role_name] if existing_user.role else ["user"]
            tokens = create_token_pair(existing_user.id, existing_user.email, roles)
            
            print(f"✅ User {email} signed in successfully")
            
            return {
                "success": True,
                "message": "OTP verified successfully",
                "user_id": existing_user.id,
                "email": existing_user.email,
                "full_name": existing_user.full_name,
                "role": existing_user.role.role_name if existing_user.role else "user",
                **tokens
            }
        else:
            # User doesn't exist - check if signup data provided
            if full_name and password:
                print(f"📝 Creating new user: email={email}, full_name={full_name}, password_length={len(password)} chars, password_bytes={len(password.encode('utf-8'))} bytes")
                
                # Create new user
                user_role = db.query(Role).filter(Role.role_name == "user").first()
                if not user_role:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Default user role not found"
                    )
                
                try:
                    password_hash = hash_password(password)
                except ValueError as e:
                    print(f"❌ Password validation error for {email}: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e)
                    )
                
                new_user = User(
                    full_name=full_name,
                    email=email,
                    phone=request.phone,
                    password_hash=password_hash,
                    role_id=user_role.role_id,
                    is_active=True,
                    is_verified=True
                )
                
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                
                roles = [user_role.role_name]
                tokens = create_token_pair(new_user.id, new_user.email, roles)
                
                print(f"✅ New user {email} signed up and verified successfully")
                
                return {
                    "success": True,
                    "message": "User created and verified successfully",
                    "user_id": new_user.id,
                    "email": new_user.email,
                    "full_name": new_user.full_name,
                    "role": user_role.role_name,
                    **tokens
                }
            else:
                # No signup data provided and user doesn't exist
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User account not found. Please sign up first or provide full_name and password."
                )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ OTP verification error for {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTP verification failed: {str(e)}"
        )


@router.post("/resend-otp")
async def resend_otp(request: SendOTPRequest, db: Session = Depends(get_db)) -> dict:
    """Resend OTP via email or phone.
    
    Args:
        request: SendOTPRequest with either 'email' or 'phone'
        db: Database session
        
    Returns:
        Success message with expiry time
    """
    email = request.email
    phone = request.phone
    
    # Validate that either email or phone is provided
    if not email and not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone number must be provided"
        )
    
    try:
        # If phone is provided, inform user that SMS OTP is not yet implemented
        if phone and not email:
            return {
                "success": False,
                "message": "OTP via phone/SMS is not yet implemented. Please use an email address to receive your OTP."
            }
        
        # Use email for OTP
        otp = OTPService.generate_numeric_otp()
        
        otp_metadata = OTPService.store_otp(
            identifier=email,
            otp=otp,
            otp_type=OTPType.EMAIL,
            expiry_minutes=5,
            phone=phone
        )
        
        # Send OTP via email
        email_sent = EmailService.send_otp_email(email, otp)
        
        if not email_sent:
            print(f"⚠️ Failed to resend email. OTP for {email}: {otp}")
            return {
                "success": False,
                "message": "Failed to resend OTP email. Please check your email configuration (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env). Check server logs for details."
            }
        
        print(f"✅ OTP resent for {email}: {otp_metadata}")
        
        # Mask email for security
        masked_email = email[:2] + "***" + email[-10:] if len(email) > 12 else email[:1] + "***" + email[-1:]
        
        return {
            "success": True,
            "message": f"OTP resent to {masked_email}",
            "identifier": masked_email,
            "expires_in_seconds": otp_metadata["ttl_seconds"],
            "otp_type": "email"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend OTP: {str(e)}"
        )
