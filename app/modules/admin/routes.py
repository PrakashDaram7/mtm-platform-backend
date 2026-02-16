"""Admin module routes with role-based access control.

This module demonstrates how to protect routes using RBAC.
All routes in this module require admin privileges.

Protection Methods:
1. require_admin - Dependency for admin-only routes
2. require_any_role - Routes accessible by multiple roles
3. require_permission - Fine-grained permission control
4. require_authenticated - Any authenticated user
"""

from typing import List
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
    RBACService,
)
from app.modules.auth.models import User, Role, Permission


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Management"],
    dependencies=[Depends(require_admin)]  # All routes require admin role
)


# User Management Routes (Admin Only)
@router.get("/users", response_model=List[dict])
async def list_all_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> List[dict]:
    """List all users in the system.
    
    Only accessible by admin role.
    
    Args:
        current_user: Admin user from dependency
        db: Database session
        skip: Number of records to skip
        limit: Maximum records to return
        
    Returns:
        List of user data
    """
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role": user.role.role_name if user.role else None,
            "created_at": user.created_at
        }
        for user in users
    ]


@router.get("/users/{user_id}", response_model=dict)
async def get_user_details(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Get details of a specific user.
    
    Only accessible by admin role.
    
    Args:
        user_id: ID of the user to retrieve
        current_user: Admin user from dependency
        db: Database session
        
    Returns:
        User details with role and permissions
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's permissions
    permissions = RBACService.get_user_permissions(user) if user.role else []
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role": user.role.role_name if user.role else None,
        "permissions": permissions,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login": user.last_login
    }


@router.patch("/users/{user_id}/role", response_model=dict)
async def update_user_role(
    user_id: str,
    role_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Update a user's role.
    
    Only accessible by admin role.
    
    Args:
        user_id: ID of the user to update
        role_id: ID of the new role
        current_user: Admin user from dependency
        db: Database session
        
    Returns:
        Updated user data
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    user.role_id = role_id
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": role.role_name,
        "message": f"User role updated to {role.role_name}"
    }


@router.patch("/users/{user_id}/status", response_model=dict)
async def toggle_user_active_status(
    user_id: str,
    is_active: bool,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Activate or deactivate a user account.
    
    Only accessible by admin role.
    
    Args:
        user_id: ID of the user to update
        is_active: New active status
        current_user: Admin user from dependency
        db: Database session
        
    Returns:
        Updated user data
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "message": f"User {'activated' if is_active else 'deactivated'}"
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Delete a user from the system.
    
    Only accessible by admin role.
    
    Args:
        user_id: ID of the user to delete
        current_user: Admin user from dependency
        db: Database session
        
    Returns:
        Confirmation message
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return {
        "message": f"User {user.email} has been deleted",
        "deleted_user_id": user_id
    }


# Role Management Routes (Admin Only)
@router.get("/roles", response_model=List[dict])
async def list_all_roles(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[dict]:
    """List all roles in the system.
    
    Only accessible by admin role.
    
    Args:
        current_user: Admin user from dependency
        db: Database session
        
    Returns:
        List of roles with permission count
    """
    roles = db.query(Role).all()
    
    return [
        {
            "role_id": role.role_id,
            "role_name": role.role_name,
            "description": role.description,
            "is_active": role.is_active,
            "permission_count": len(role.permissions),
            "created_at": role.created_at
        }
        for role in roles
    ]


@router.get("/roles/{role_id}", response_model=dict)
async def get_role_details(
    role_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Get details of a specific role with all permissions.
    
    Only accessible by admin role.
    
    Args:
        role_id: ID of the role to retrieve
        current_user: Admin user from dependency
        db: Database session
        
    Returns:
        Role details with associated permissions
    """
    role = db.query(Role).filter(Role.role_id == role_id).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return {
        "role_id": role.role_id,
        "role_name": role.role_name,
        "description": role.description,
        "is_active": role.is_active,
        "permissions": [
            {
                "permission_id": perm.permission_id,
                "permission_name": perm.permission_name,
                "resource": perm.resource,
                "action": perm.action,
                "description": perm.description
            }
            for perm in role.permissions
        ],
        "user_count": len(role.users),
        "created_at": role.created_at
    }


@router.post("/roles", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_name: str,
    description: str = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Create a new role.
    
    Only accessible by admin role.
    
    Args:
        role_name: Name of the new role
        description: Role description
        current_user: Admin user from dependency
        db: Database session
        
    Returns:
        Created role data
    """
    # Check if role already exists
    existing_role = db.query(Role).filter(Role.role_name == role_name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_name}' already exists"
        )
    
    new_role = Role(
        role_name=role_name,
        description=description,
        is_active=True
    )
    
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return {
        "role_id": new_role.role_id,
        "role_name": new_role.role_name,
        "description": new_role.description,
        "is_active": new_role.is_active,
        "message": f"Role '{role_name}' created successfully"
    }


# System Statistics Routes
@router.get("/statistics", response_model=dict)
async def get_system_statistics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Get system-wide statistics.
    
    Only accessible by admin role.
    
    Args:
        current_user: Admin user from dependency
        db: Database session
        
    Returns:
        System statistics
    """
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    total_roles = db.query(Role).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "inactive_users": total_users - active_users,
        "total_roles": total_roles,
        "timestamp": "datetime"
    }


@router.get("/audit-log", response_model=List[dict])
async def get_audit_log(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 50
) -> List[dict]:
    """Get admin action audit log.
    
    Only accessible by admin role.
    
    Note: This is a placeholder. Implement actual audit logging as needed.
    
    Args:
        current_user: Admin user from dependency
        db: Database session
        limit: Number of log entries to retrieve
        
    Returns:
        List of audit log entries
    """
    return [
        {
            "id": "1",
            "action": "User role updated",
            "admin": current_user.email,
            "target": "user@example.com",
            "details": "Role changed from user to moderator",
            "timestamp": "2024-02-16T10:30:00Z"
        }
    ]
