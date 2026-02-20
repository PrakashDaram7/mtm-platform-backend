"""Role-Based Access Control (RBAC) Middleware and Dependencies.

Aligned with PRD Section 3.1 roles:
  admin, finance_admin, event_manager, committee_member,
  moderator, member, family_member, volunteer
"""

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
        """Require a specific role."""
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
        """Require any of multiple roles."""
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
        """Require specific resource permission."""
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

        # Admin has full access
        if user.role.role_name == "admin":
            return user

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


# ─── Convenience dependency functions ───────────────────────────────────────

def require_admin(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require admin role."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_role(user, "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_finance_admin(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require finance_admin or admin role."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "finance_admin"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finance Admin access required")
    return user


def require_event_manager(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require event_manager or admin role."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "event_manager"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event Manager access required")
    return user


def require_committee_member(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require committee_member or admin role."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "committee_member"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Committee Member access required")
    return user


def require_moderator(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require moderator or admin role."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "moderator"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator access required")
    return user


def require_member(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require member role (or any higher role)."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "finance_admin", "event_manager", "committee_member", "moderator", "member"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Member access required")
    return user


def require_authenticated(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require any authenticated user."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    return user


def get_current_authenticated_user(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user (no role requirement)."""
    return require_authenticated(current_user, db)
