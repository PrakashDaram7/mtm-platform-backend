"""Sample test routes demonstrating RBAC functionality for different roles.

This module provides example endpoints that demonstrate role-based
access control for Admin, Moderator, and User roles.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import (
    get_current_user,
    get_db,
    get_user_from_db,
    TokenData,
    user_has_role,
    user_has_any_role,
    RBACService,
)
from app.modules.auth.models import User

router = APIRouter(
    prefix="/api/test",
    tags=["testing"],
    responses={404: {"description": "Not found"}}
)


# ==================== PUBLIC ROUTES ====================

@router.get("/public/info")
async def public_info() -> dict:
    """Public endpoint - no authentication required."""
    return {
        "message": "This is a public endpoint",
        "status": "accessible",
        "requires_auth": False
    }


# ==================== AUTHENTICATED USER ROUTES ====================

@router.get("/user/dashboard")
async def user_dashboard(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """User dashboard - requires authentication."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "message": f"Welcome to your dashboard, {user.full_name}!",
        "user_id": user.id,
        "email": user.email,
        "role": user.role.role_name if user.role else "No role",
        "account_active": user.is_active,
        "verified": user.is_verified,
        "dashboard_type": "personal"
    }


@router.get("/user/profile")
async def user_profile(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get user's own profile."""
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
        "role": user.role.role_name if user.role else None,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None
    }


@router.get("/user/permissions")
async def user_permissions(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get current user's permissions."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    permissions = RBACService.get_user_permissions(user)
    
    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.role_name if user.role else None,
        "total_permissions": len(permissions),
        "permissions": permissions
    }


# ==================== MODERATOR-ONLY ROUTES ====================

@router.get("/moderator/dashboard")
async def moderator_dashboard(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Moderator dashboard - moderator or admin only."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_any_role(user, ["moderator", "admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Moderator or Admin role"
        )
    
    return {
        "message": f"Welcome to moderator dashboard, {user.full_name}!",
        "role": user.role.role_name,
        "total_users": db.query(User).count(),
        "moderator_features": [
            "View user reports",
            "Manage content",
            "Review flagged items",
            "Send notifications"
        ],
        "dashboard_type": "moderation"
    }


@router.get("/moderator/users-list")
async def moderator_users_list(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20
) -> dict:
    """List users for moderation - moderator or admin only."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_any_role(user, ["moderator", "admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Moderator or Admin role"
        )
    
    users = db.query(User).limit(limit).all()
    
    return {
        "total_users": db.query(User).count(),
        "limit": limit,
        "users_returned": len(users),
        "users": [
            {
                "id": u.id,
                "name": u.full_name,
                "email": u.email,
                "role": u.role.role_name if u.role else None,
                "is_active": u.is_active,
                "verified": u.is_verified
            }
            for u in users
        ]
    }


@router.post("/moderator/flag-user/{user_id}")
async def flag_user(
    user_id: str,
    reason: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Flag a user for review - moderator or admin only."""
    moderator = get_user_from_db(current_user.user_id, db)
    
    if not moderator or not user_has_any_role(moderator, ["moderator", "admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Moderator or Admin role"
        )
    
    user = get_user_from_db(user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "message": f"User {user.email} has been flagged",
        "flagged_user_id": user_id,
        "flagged_by": moderator.email,
        "reason": reason,
        "action": "User is marked for admin review"
    }


# ==================== ADMIN-ONLY ROUTES ====================

@router.get("/admin/dashboard")
async def admin_dashboard(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Admin dashboard - admin only."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_role(user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Admin role"
        )
    
    return {
        "message": f"Welcome to admin dashboard, {user.full_name}!",
        "role": user.role.role_name,
        "statistics": {
            "total_users": db.query(User).count(),
            "active_users": db.query(User).filter(User.is_active == True).count(),
            "verified_users": db.query(User).filter(User.is_verified == True).count(),
            "inactive_users": db.query(User).filter(User.is_active == False).count()
        },
        "admin_features": [
            "User management",
            "Role assignment",
            "Permission control",
            "System settings",
            "Audit logs",
            "Analytics"
        ],
        "dashboard_type": "administration"
    }


@router.get("/admin/system-stats")
async def admin_system_stats(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """System statistics - admin only."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_role(user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Admin role"
        )
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    
    return {
        "system_status": "operational",
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "inactive_users": total_users - active_users,
        "active_percentage": f"{(active_users/total_users*100):.2f}%" if total_users > 0 else "0%",
        "verified_percentage": f"{(verified_users/total_users*100):.2f}%" if total_users > 0 else "0%",
        "system_health": {
            "database": "connected",
            "authentication": "operational",
            "rbac": "operational"
        }
    }


@router.post("/admin/bulk-role-assign")
async def bulk_role_assign(
    role_assignment: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Bulk assign roles to users - admin only."""
    admin = get_user_from_db(current_user.user_id, db)
    
    if not admin or not user_has_role(admin, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Admin role"
        )
    
    user_ids = role_assignment.get("user_ids", [])
    new_role_name = role_assignment.get("role_name")
    
    if not user_ids or not new_role_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_ids and role_name are required"
        )
    
    return {
        "success": True,
        "message": f"Role assignment initiated",
        "operation": "bulk_role_assign",
        "users_affected": len(user_ids),
        "new_role": new_role_name,
        "assigned_by": admin.email,
        "status": "completed"
    }


@router.delete("/admin/delete-user/{user_id}")
async def admin_delete_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Permanently delete a user - admin only."""
    admin = get_user_from_db(current_user.user_id, db)
    
    if not admin or not user_has_role(admin, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Admin role"
        )
    
    user_to_delete = get_user_from_db(user_id, db)
    
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_to_delete.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    deleted_user_email = user_to_delete.email
    db.delete(user_to_delete)
    db.commit()
    
    return {
        "success": True,
        "message": f"User {deleted_user_email} has been permanently deleted",
        "deleted_user_id": user_id,
        "deleted_by": admin.email,
        "timestamp": "2024-02-16T00:00:00Z"
    }


@router.post("/admin/system-maintenance")
async def admin_system_maintenance(
    maintenance_task: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Perform system maintenance - admin only."""
    admin = get_user_from_db(current_user.user_id, db)
    
    if not admin or not user_has_role(admin, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires Admin role"
        )
    
    task_type = maintenance_task.get("task_type", "unknown")
    
    return {
        "success": True,
        "message": f"Maintenance task '{task_type}' initiated",
        "task_type": task_type,
        "initiated_by": admin.email,
        "status": "in_progress",
        "expected_duration": "5-10 minutes"
    }


# ==================== RBAC TESTING ROUTES ====================

@router.get("/test/role-check/{user_id}")
async def test_role_check(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Test endpoint to check user roles - admin only."""
    admin = get_user_from_db(current_user.user_id, db)
    
    if not admin or not user_has_role(admin, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    target_user = get_user_from_db(user_id, db)
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "user_id": target_user.id,
        "email": target_user.email,
        "full_name": target_user.full_name,
        "role": {
            "role_id": target_user.role.role_id if target_user.role else None,
            "role_name": target_user.role.role_name if target_user.role else None
        },
        "is_admin": user_has_role(target_user, "admin"),
        "is_moderator": user_has_role(target_user, "moderator"),
        "is_user": user_has_role(target_user, "user"),
        "permissions_count": len(target_user.role.permissions) if target_user.role else 0
    }


@router.get("/test/permission-check/{resource}/{action}")
async def test_permission_check(
    resource: str,
    action: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Test endpoint to check permissions - for testing RBAC."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    has_permission = RBACService.check_permission(user, resource, action)
    
    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.role_name if user.role else None,
        "resource": resource,
        "action": action,
        "has_permission": has_permission,
        "all_permissions": RBACService.get_user_permissions(user)
    }
