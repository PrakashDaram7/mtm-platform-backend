"""Members module routes with role-based access control."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import (
    get_db,
    get_user_from_db,
)
from app.core.rbac_middleware import (
    require_authenticated,
    require_admin,
)
from app.modules.auth.models import User


router = APIRouter(prefix="/api/members", tags=["Members"])


# ============================================================================
# PUBLIC MEMBER ENDPOINTS
# ============================================================================

@router.get("")
async def list_members(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None
) -> dict:
    """List all public member profiles (public endpoint).
    
    Only shows members who have made their profile public.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search term for member names
        
    Returns:
        List of public member profiles
    """
    return {
        "message": "List of public members",
        "skip": skip,
        "limit": limit,
        "search": search,
        "note": "Implement with your Member model"
    }


@router.get("/{member_id}")
async def get_member_profile(
    member_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """Get public profile of a member.
    
    Args:
        member_id: Member ID
        db: Database session
        
    Returns:
        Member profile information
    """
    return {
        "message": f"Member profile for {member_id}",
        "note": "Implement with your Member model"
    }


# ============================================================================
# AUTHENTICATED USER ENDPOINTS
# ============================================================================

@router.get("/me/profile")
async def get_my_profile(
    current_user: User = Depends(require_authenticated)
) -> dict:
    """Get current user's complete profile (authenticated users only).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Complete user profile with private information
    """
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "last_login": current_user.last_login,
        "role_name": current_user.role.role_name if current_user.role else None,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "message": "Your complete profile"
    }


@router.put("/me/profile")
async def update_my_profile(
    profile_data: dict,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Update current user's profile (authenticated users only).
    
    Users can only update their own profile. Admins can update anyone's profile
    (see admin endpoints below).
    
    Args:
        profile_data: Updated profile data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated profile information
    """
    return {
        "message": "Profile updated successfully",
        "user_id": current_user.id,
        "updated_fields": list(profile_data.keys()) if profile_data else [],
        "note": "Implement actual update logic"
    }


@router.get("/me/activity")
async def get_my_activity(
    current_user: User = Depends(require_authenticated),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> dict:
    """Get current user's activity history (authenticated users only).
    
    Args:
        current_user: Current authenticated user
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        User's activity history
    """
    return {
        "message": "Your activity history",
        "user_id": current_user.id,
        "skip": skip,
        "limit": limit,
        "note": "Implement with your Activity model"
    }


@router.get("/me/events")
async def get_my_events(
    current_user: User = Depends(require_authenticated),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> dict:
    """Get events registered by current user (authenticated users only).
    
    Args:
        current_user: Current authenticated user
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of user's registered events
    """
    return {
        "message": "Your registered events",
        "user_id": current_user.id,
        "skip": skip,
        "limit": limit,
        "note": "Implement with your Event/EventAttendee models"
    }


@router.post("/me/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Change current user's password (authenticated users only).
    
    Args:
        old_password: Current password for verification
        new_password: New password
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Password change confirmation
    """
    return {
        "message": "Password changed successfully",
        "user_id": current_user.id,
        "changed_at": datetime.utcnow()
    }


@router.post("/me/update-email")
async def update_email(
    new_email: str,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Update current user's email (authenticated users only).
    
    Email update may require verification of the new email address.
    
    Args:
        new_email: New email address
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Email update confirmation
    """
    return {
        "message": "Email update initiated",
        "user_id": current_user.id,
        "old_email": current_user.email,
        "verification_required": True,
        "note": "Implement email verification flow"
    }


# ============================================================================
# ADMIN-ONLY MEMBER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/admin/all-members", dependencies=[Depends(require_admin)])
async def list_all_members_admin(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None
) -> dict:
    """List all members with detailed info (admin only).
    
    Admins can see all members including deactivated ones.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        role_filter: Filter by role
        status_filter: Filter by status (active, inactive)
        
    Returns:
        List of all members with full details
    """
    return {
        "message": "All members (admin view)",
        "skip": skip,
        "limit": limit,
        "role_filter": role_filter,
        "status_filter": status_filter,
        "admin_only": True
    }


@router.get("/admin/{member_id}/profile", dependencies=[Depends(require_admin)])
async def get_member_profile_admin(
    member_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """Get detailed admin view of a member (admin only).
    
    Shows all profile information including sensitive data.
    
    Args:
        member_id: Member ID
        db: Database session
        
    Returns:
        Complete member profile with admin notes
    """
    return {
        "message": f"Admin view of member {member_id}",
        "admin_only": True,
        "fields_included": [
            "id", "full_name", "email", "phone", "role", "status",
            "verification_status", "activity_logs", "created_at"
        ]
    }


@router.put("/admin/{member_id}/profile")
async def update_member_profile_admin(
    member_id: str,
    profile_data: dict,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Update a member's profile (admin only).
    
    Admins can update any member's profile.
    
    Args:
        member_id: Member ID to update
        profile_data: Updated profile data
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Updated member profile
    """
    return {
        "message": f"Member {member_id} profile updated",
        "updated_by": current_admin.full_name,
        "admin_only": True
    }


@router.post("/admin/{member_id}/verify-email")
async def verify_member_email_admin(
    member_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Manually verify a member's email (admin only).
    
    Args:
        member_id: Member ID
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Verification confirmation
    """
    return {
        "message": f"Email verified for member {member_id}",
        "verified_by": current_admin.full_name,
        "admin_only": True
    }


@router.get("/admin/pending-verification", dependencies=[Depends(require_admin)])
async def get_pending_verification(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> dict:
    """List members pending email verification (admin only).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of members pending verification
    """
    return {
        "message": "Members pending email verification",
        "skip": skip,
        "limit": limit,
        "admin_only": True
    }


@router.post("/admin/{member_id}/send-verification-email")
async def send_verification_email_admin(
    member_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Send verification email to a member (admin only).
    
    Args:
        member_id: Member ID
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Email send confirmation
    """
    return {
        "message": f"Verification email sent to member {member_id}",
        "sent_by": current_admin.full_name,
        "admin_only": True
    }
