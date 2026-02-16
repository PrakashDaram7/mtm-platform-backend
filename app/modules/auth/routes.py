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
    UserResponseSchema,
    UserDetailSchema,
    ChangePasswordSchema,
)

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
    
    # Create new user
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=hash_password(user_data.password),
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
    
    user.password_hash = hash_password(password_data.new_password)
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


@router.get("/users")
async def list_users(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10
) -> dict:
    """List all users (admin only).
    
    Args:
        current_user: Current authenticated user
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records
        
    Returns:
        List of users
    """
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_role(user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": [
            {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "role_name": user.role.role_name if user.role else None,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Update user role (admin only).
    
    Args:
        user_id: User ID to update
        role_data: Dictionary with 'role_name'
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Updated user data
    """
    admin = get_user_from_db(current_user.user_id, db)
    
    if not admin or not user_has_role(admin, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    user = get_user_from_db(user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    role_name = role_data.get("role_name")
    if not role_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_name is required"
        )
    
    role = db.query(Role).filter(Role.role_name == role_name).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found"
        )
    
    user.role_id = role.role_id
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "previous_role": user.role.role_name if user.role else None,
        "new_role": role.role_name,
        "success": True
    }


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Disable a user account (admin only).
    
    Args:
        user_id: User ID to disable
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Updated user data
    """
    admin = get_user_from_db(current_user.user_id, db)
    
    if not admin or not user_has_role(admin, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    user = get_user_from_db(user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "success": True
    }


@router.post("/users/{user_id}/enable")
async def enable_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Enable a disabled user account (admin only).
    
    Args:
        user_id: User ID to enable
        current_user: Current authenticated user (must be admin)
        db: Database session
        
    Returns:
        Updated user data
    """
    admin = get_user_from_db(current_user.user_id, db)
    
    if not admin or not user_has_role(admin, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    user = get_user_from_db(user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "success": True
    }

