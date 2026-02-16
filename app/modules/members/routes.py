"""Members module routes with role-based access control.

This module demonstrates protected routes for member management.
Different routes have different protection levels:

1. User profile routes - Require authenticated user
2. Member list - Accessible by moderators and admins
3. Member management - Admin only
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import (
    get_db,
    require_admin,
    require_any_role,
    require_permission,
    require_authenticated,
    get_current_authenticated_user,
)
from app.modules.auth.models import User


router = APIRouter(
    prefix="/api/members",
    tags=["Members"]
)


# Profile Routes - Any Authenticated User
@router.get("/profile", response_model=dict)
async def get_my_profile(
    current_user: User = Depends(require_authenticated)
) -> dict:
    """Get current user's profile.
    
    Accessible by any authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile information
    """
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "role": current_user.role.role_name if current_user.role else None,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }


@router.patch("/profile", response_model=dict)
async def update_my_profile(
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Update current user's profile.
    
    Accessible by any authenticated user.
    
    Args:
        full_name: Updated full name
        phone: Updated phone number
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated profile information
    """
    if full_name:
        current_user.full_name = full_name
    if phone:
        current_user.phone = phone
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "message": "Profile updated successfully"
    }


@router.get("/profile/{user_id}", response_model=dict)
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Get another user's profile.
    
    Accessible by any authenticated user.
    
    Args:
        user_id: ID of the user to retrieve
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User profile information
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "role": user.role.role_name if user.role else None,
        "created_at": user.created_at
    }


# Member List Routes - Moderators and Admins
@router.get("/", response_model=List[dict])
async def list_members(
    current_user: User = Depends(require_any_role(["admin", "moderator"])),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    role_filter: Optional[str] = None
) -> List[dict]:
    """List all members (moderators and admins only).
    
    Protected by require_any_role - accessible by admin OR moderator
    
    Args:
        current_user: Moderator or admin user
        db: Database session
        skip: Number of records to skip
        limit: Maximum records to return
        role_filter: Optional filter by role name
        
    Returns:
        List of member profiles
    """
    query = db.query(User)
    
    if role_filter:
        query = query.join(User.role).filter(
            User.role.role_name == role_filter
        )
    
    members = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": member.id,
            "full_name": member.full_name,
            "email": member.email,
            "phone": member.phone,
            "is_active": member.is_active,
            "is_verified": member.is_verified,
            "role": member.role.role_name if member.role else None,
            "created_at": member.created_at
        }
        for member in members
    ]


@router.get("/active", response_model=List[dict])
async def list_active_members(
    current_user: User = Depends(require_any_role(["admin", "moderator"])),
    db: Session = Depends(get_db),
    limit: int = 50
) -> List[dict]:
    """List active members only (moderators and admins).
    
    Args:
        current_user: Moderator or admin user
        db: Database session
        limit: Maximum records to return
        
    Returns:
        List of active member profiles
    """
    members = db.query(User).filter(User.is_active == True).limit(limit).all()
    
    return [
        {
            "id": member.id,
            "full_name": member.full_name,
            "email": member.email,
            "role": member.role.role_name if member.role else None,
            "last_login": member.last_login
        }
        for member in members
    ]


# Member Management Routes - Admin Only
@router.patch("/{user_id}/verify", response_model=dict)
async def verify_member(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Verify a member (admin only).
    
    Args:
        user_id: ID of the user to verify
        current_user: Admin user
        db: Database session
        
    Returns:
        Updated member info
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    user.is_verified = True
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_verified": True,
        "message": "Member verified successfully"
    }


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def remove_member(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Remove a member from the platform (admin only).
    
    Args:
        user_id: ID of the member to remove
        current_user: Admin user
        db: Database session
        
    Returns:
        Confirmation message
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    user_email = user.email
    db.delete(user)
    db.commit()
    
    return {
        "message": f"Member {user_email} has been removed",
        "removed_user_id": user_id
    }


# Statistics Routes - Moderators and Admins
@router.get("/stats/summary", response_model=dict)
async def get_members_summary(
    current_user: User = Depends(require_any_role(["admin", "moderator"])),
    db: Session = Depends(get_db)
) -> dict:
    """Get summary statistics about members.
    
    Accessible by moderators and admins.
    
    Args:
        current_user: Moderator or admin user
        db: Database session
        
    Returns:
        Member statistics
    """
    total = db.query(User).count()
    active = db.query(User).filter(User.is_active == True).count()
    verified = db.query(User).filter(User.is_verified == True).count()
    
    return {
        "total_members": total,
        "active_members": active,
        "verified_members": verified,
        "unverified_members": total - verified,
        "inactive_members": total - active
    }

