"""Authentication and Authorization routes with RBAC support."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    hash_password,
    get_current_user,
    get_db,
    get_user_from_db,
    TokenData,
)
from app.core.rbac_middleware import (
    require_admin,
    require_user,
    require_moderator,
    get_current_authenticated_user,
    RBACMiddleware,
)
from app.modules.auth.models import User, Role
from app.modules.auth.schemas import UserLoginSchema, UserRegisterSchema, TokenResponseSchema, UserResponseSchema


router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterSchema,
    db: Session = Depends(get_db)
) -> dict:
    """Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        Created user data
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
            detail="Default user role not found. Please create roles first."
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
async def login(
    credentials: UserLoginSchema,
    db: Session = Depends(get_db)
) -> dict:
    """Login user and return access token.
    
    Args:
        credentials: User login credentials
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


@router.get("/me", response_model=UserResponseSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_authenticated_user)
) -> dict:
    """Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user data
    """
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "role_name": current_user.role.role_name if current_user.role else None
    }


@router.get("/admin-only")
async def admin_endpoint(
    current_user: User = Depends(require_admin)
) -> dict:
    """Admin-only protected route.
    
    Args:
        current_user: Current user (must be admin)
        
    Returns:
        Success message
    """
    return {
        "message": f"Welcome to admin section, {current_user.full_name}",
        "role": current_user.role.role_name if current_user.role else None
    }


@router.get("/moderator-only")
async def moderator_endpoint(
    current_user: User = Depends(require_moderator)
) -> dict:
    """Moderator-only protected route.
    
    Args:
        current_user: Current user (must be moderator)
        
    Returns:
        Success message
    """
    return {
        "message": f"Welcome to moderator section, {current_user.full_name}",
        "role": current_user.role.role_name if current_user.role else None
    }


@router.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_authenticated_user)
) -> dict:
    """Protected route requiring authentication.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    return {
        "message": f"Hello {current_user.full_name}, this is a protected route",
        "role": current_user.role.role_name if current_user.role else None
    }


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10
) -> list:
    """List all users (admin only).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records
        
    Returns:
        List of users
    """
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role_name": user.role.role_name if user.role else None
        }
        for user in users
    ]


@router.put("/users/{user_id}/role", dependencies=[Depends(require_admin)])
async def update_user_role(
    user_id: str,
    role_name: str,
    db: Session = Depends(get_db)
) -> dict:
    """Update user role (admin only).
    
    Args:
        user_id: User ID
        role_name: New role name
        db: Database session
        
    Returns:
        Updated user data
    """
    user = get_user_from_db(user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
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
        "new_role": role.role_name
    }


@router.post("/users/{user_id}/disable", dependencies=[Depends(require_admin)])
async def disable_user(
    user_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """Disable a user account (admin only).
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        Updated user data
    """
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
        "is_active": user.is_active
    }

