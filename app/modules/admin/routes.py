"""Admin module routes with role-based access control."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import (
    get_db,
    get_user_from_db,
)
from app.core.rbac_middleware import (
    require_admin,
    RBACMiddleware,
)
from app.modules.auth.models import User, Role
from app.modules.auth.schemas import UserResponseSchema


router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ============================================================================
# USER MANAGEMENT ENDPOINTS (Admin Only)
# ============================================================================

@router.get("/users", dependencies=[Depends(require_admin)])
async def list_all_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role_filter: Optional[str] = None,
    is_active: Optional[bool] = None
) -> list:
    """List all users with optional filtering (admin only).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        role_filter: Filter by role name
        is_active: Filter by active status
        
    Returns:
        List of users with their details
    """
    query = db.query(User)
    
    if role_filter:
        query = query.join(Role).filter(Role.role_name == role_filter)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login": user.last_login,
            "role_name": user.role.role_name if user.role else None,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        for user in users
    ]


@router.get("/users/{user_id}", dependencies=[Depends(require_admin)])
async def get_user_details(
    user_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """Get detailed information for a specific user (admin only).
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        User details including role and permissions
    """
    user = get_user_from_db(user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    permissions = []
    if user.role and user.role.permissions:
        permissions = [
            {
                "permission_name": perm.permission_name,
                "resource": perm.resource,
                "action": perm.action,
                "description": perm.description
            }
            for perm in user.role.permissions
        ]
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "last_login": user.last_login,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "role": {
            "role_id": user.role.role_id if user.role else None,
            "role_name": user.role.role_name if user.role else None,
            "description": user.role.description if user.role else None,
            "permissions": permissions
        }
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_name: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Update a user's role (admin only).
    
    Args:
        user_id: User ID to update
        role_name: New role name
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Updated user information
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
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
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "previous_role": user.role.role_name if user.role else None,
        "new_role": role.role_name,
        "updated_at": user.updated_at
    }


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Activate a disabled user account (admin only).
    
    Args:
        user_id: User ID to activate
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Updated user information
    """
    user = get_user_from_db(user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active"
        )
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "updated_at": user.updated_at
    }


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    reason: Optional[str] = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Deactivate a user account (admin only).
    
    Args:
        user_id: User ID to deactivate
        reason: Reason for deactivation (optional)
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Updated user information
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user = get_user_from_db(user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already inactive"
        )
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "deactivation_reason": reason,
        "updated_at": user.updated_at
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Delete a user permanently (admin only).
    
    Args:
        user_id: User ID to delete
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Deletion confirmation
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = get_user_from_db(user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_email = user.email
    db.delete(user)
    db.commit()
    
    return {
        "message": "User deleted successfully",
        "deleted_user_email": user_email,
        "user_id": user_id
    }


# ============================================================================
# ROLE MANAGEMENT ENDPOINTS (Admin Only)
# ============================================================================

@router.get("/roles", dependencies=[Depends(require_admin)])
async def list_all_roles(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> list:
    """List all available roles (admin only).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of roles with permissions
    """
    roles = db.query(Role).offset(skip).limit(limit).all()
    
    return [
        {
            "role_id": role.role_id,
            "role_name": role.role_name,
            "description": role.description,
            "is_active": role.is_active,
            "permissions_count": len(role.permissions) if role.permissions else 0,
            "user_count": len(role.users) if role.users else 0,
            "created_at": role.created_at,
            "updated_at": role.updated_at
        }
        for role in roles
    ]


@router.get("/roles/{role_name}", dependencies=[Depends(require_admin)])
async def get_role_details(
    role_name: str,
    db: Session = Depends(get_db)
) -> dict:
    """Get detailed information for a specific role (admin only).
    
    Args:
        role_name: Role name
        db: Database session
        
    Returns:
        Role details with permissions and associated users
    """
    role = db.query(Role).filter(Role.role_name == role_name).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found"
        )
    
    permissions = []
    if role.permissions:
        permissions = [
            {
                "permission_id": perm.permission_id,
                "permission_name": perm.permission_name,
                "resource": perm.resource,
                "action": perm.action,
                "description": perm.description
            }
            for perm in role.permissions
        ]
    
    users = []
    if role.users:
        users = [
            {
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email
            }
            for user in role.users
        ]
    
    return {
        "role_id": role.role_id,
        "role_name": role.role_name,
        "description": role.description,
        "is_active": role.is_active,
        "created_at": role.created_at,
        "updated_at": role.updated_at,
        "permissions": permissions,
        "users": users,
        "user_count": len(users)
    }


# ============================================================================
# SYSTEM STATISTICS ENDPOINTS (Admin Only)
# ============================================================================

@router.get("/stats/summary", dependencies=[Depends(require_admin)])
async def get_system_statistics(
    db: Session = Depends(get_db)
) -> dict:
    """Get system statistics summary (admin only).
    
    Args:
        db: Database session
        
    Returns:
        System statistics including user counts, role distribution
    """
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    
    role_distribution = []
    roles = db.query(Role).all()
    for role in roles:
        role_user_count = db.query(User).filter(User.role_id == role.role_id).count()
        role_distribution.append({
            "role_name": role.role_name,
            "user_count": role_user_count
        })
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "verified_users": verified_users,
        "unverified_users": total_users - verified_users,
        "role_distribution": role_distribution,
        "timestamp": datetime.utcnow()
    }


@router.get("/stats/users/activity", dependencies=[Depends(require_admin)])
async def get_user_activity_stats(
    db: Session = Depends(get_db)
) -> dict:
    """Get user activity statistics (admin only).
    
    Args:
        db: Database session
        
    Returns:
        User activity statistics
    """
    total_users = db.query(User).count()
    
    # Count users by verification status
    verified = db.query(User).filter(User.is_verified == True).count()
    unverified = db.query(User).filter(User.is_verified == False).count()
    
    # Count users by active status
    active = db.query(User).filter(User.is_active == True).count()
    inactive = db.query(User).filter(User.is_active == False).count()
    
    # Count users with/without last login
    with_login = db.query(User).filter(User.last_login != None).count()
    without_login = db.query(User).filter(User.last_login == None).count()
    
    return {
        "total_users": total_users,
        "verification": {
            "verified": verified,
            "unverified": unverified
        },
        "status": {
            "active": active,
            "inactive": inactive
        },
        "activity": {
            "logged_in": with_login,
            "never_logged_in": without_login
        }
    }
