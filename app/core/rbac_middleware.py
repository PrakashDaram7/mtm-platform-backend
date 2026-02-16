"""Role-Based Access Control (RBAC) Middleware and Dependencies."""

from typing import List, Callable, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    get_current_user,
    TokenData,
    get_db,
    get_user_from_db,
    user_has_role,
    user_has_any_role,
)
from app.modules.auth.models import User


class RBACMiddleware:
    """Middleware for role-based access control on routes."""
    
    @staticmethod
    async def require_role(
        required_role: str,
        current_user: TokenData = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Dependency to require a specific role.
        
        Args:
            required_role: Role name required (e.g., 'admin', 'user')
            current_user: Current user from token
            db: Database session
            
        Returns:
            User object if authorized
            
        Raises:
            HTTPException: If user doesn't have required role
        """
        user = get_user_from_db(current_user.user_id, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user_has_role(user, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}",
            )
        
        return user
    
    @staticmethod
    async def require_any_role(
        required_roles: List[str],
        current_user: TokenData = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Dependency to require any of multiple roles.
        
        Args:
            required_roles: List of allowed role names
            current_user: Current user from token
            db: Database session
            
        Returns:
            User object if authorized
            
        Raises:
            HTTPException: If user doesn't have any required role
        """
        user = get_user_from_db(current_user.user_id, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user_has_any_role(user, required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}",
            )
        
        return user
    
    @staticmethod
    async def require_permission(
        resource: str,
        action: str,
        current_user: TokenData = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Dependency to require specific resource permission.
        
        Args:
            resource: Resource name (e.g., 'users', 'events', 'payments')
            action: Action name (e.g., 'create', 'read', 'update', 'delete')
            current_user: Current user from token
            db: Database session
            
        Returns:
            User object if authorized
            
        Raises:
            HTTPException: If user doesn't have required permission
        """
        user = get_user_from_db(current_user.user_id, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user or not user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no role assigned",
            )
        
        # Check permission
        has_permission = False
        for permission in user.role.permissions:
            if permission.resource == resource and permission.action == action:
                has_permission = True
                break
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {action} on {resource}",
            )
        
        return user


def require_admin(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to require admin role."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_role(user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return user


def require_user(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to require user role."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_role(user, "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User access required",
        )
    
    return user


def require_moderator(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to require moderator role."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user or not user_has_role(user, "moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )
    
    return user


def require_authenticated(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to require any authenticated user."""
    user = get_user_from_db(current_user.user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


def get_current_authenticated_user(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user (no role requirement)."""
    return require_authenticated(current_user, db)
