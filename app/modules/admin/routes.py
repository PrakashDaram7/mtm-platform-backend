"""Admin module routes for user management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import (
    get_current_user,
    get_db,
    get_user_from_db,
    TokenData,
    user_has_role,
)
from app.modules.admin.services import AdminUserService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}}
)


def check_admin_role(current_user: TokenData, db: Session) -> bool:
    """Check if current user has admin role."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_role(user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    return True


@router.get("/users")
async def list_users(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10
):
    """Get all users with pagination (admin only)."""
    check_admin_role(current_user, db)
    
    result = AdminUserService.get_all_users(db, skip, limit)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed user information (admin only)."""
    check_admin_role(current_user, db)
    
    result = AdminUserService.get_user_detail(db, user_id)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )


@router.post("/users")
async def create_user(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only).
    
    Request body:
    {
        "full_name": "string",
        "email": "string",
        "phone": "string (optional)",
        "password": "string (optional)",
        "role_name": "string (optional, default: user)"
    }
    """
    check_admin_role(current_user, db)
    
    full_name = request.get("full_name")
    email = request.get("email")
    phone = request.get("phone")
    role_name = request.get("role_name", "member")
    
    if not full_name or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name and email are required"
        )
    
    result = AdminUserService.create_user(db, full_name, email, phone, role_name)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user information (admin only).
    
    Request body (all optional):
    {
        "full_name": "string",
        "phone": "string",
        "is_active": "boolean",
        "is_verified": "boolean",
        "role_name": "string"
    }
    """
    check_admin_role(current_user, db)
    
    result = AdminUserService.update_user(db, user_id, **request)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if "not found" not in result["message"].lower() else status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)."""
    check_admin_role(current_user, db)
    
    result = AdminUserService.delete_user(db, user_id)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable a user account (admin only)."""
    check_admin_role(current_user, db)
    
    result = AdminUserService.disable_user(db, user_id)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )


@router.post("/users/{user_id}/enable")
async def enable_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable a disabled user account (admin only)."""
    check_admin_role(current_user, db)
    
    result = AdminUserService.enable_user(db, user_id)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user role (admin only).
    
    Request body:
    {
        "role_name": "string"
    }
    """
    check_admin_role(current_user, db)
    
    role_name = request.get("role_name")
    if not role_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_name is required"
        )
    
    result = AdminUserService.change_user_role(db, user_id, role_name)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if "not found" not in result["message"].lower() else status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )


@router.get("/users/search")
async def search_users(
    query: str,
    field: str = "email",
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by field (admin only).
    
    Query parameters:
    - query: Search query string
    - field: Field to search in (email, full_name, phone)
    """
    check_admin_role(current_user, db)
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query is required"
        )
    
    result = AdminUserService.search_users(db, query, field)
    return result


@router.get("/analytics")
async def get_analytics(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard analytics data (admin only)."""
    check_admin_role(current_user, db)
    
    result = AdminUserService.get_analytics(db)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )


# ==================== ROLE MANAGEMENT ROUTES ====================

@router.get("/roles")
async def list_roles(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all roles (admin only)."""
    check_admin_role(current_user, db)
    
    result = AdminUserService.get_all_roles(db)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )


@router.post("/roles")
async def create_role(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new role (admin only).
    
    Request body:
    {
        "role_name": "string",
        "description": "string (optional)"
    }
    """
    check_admin_role(current_user, db)
    
    role_name = request.get("role_name")
    description = request.get("description")
    
    if not role_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_name is required"
        )
    
    result = AdminUserService.create_role(db, role_name, description)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )


@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a role (admin only).
    
    Request body:
    {
        "role_name": "string (optional)",
        "description": "string (optional)"
    }
    """
    check_admin_role(current_user, db)
    
    role_name = request.get("role_name")
    description = request.get("description")
    
    result = AdminUserService.update_role(db, role_id, role_name, description)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if "already exists" in result["message"] else status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a role (admin only)."""
    check_admin_role(current_user, db)
    
    result = AdminUserService.delete_role(db, role_id)
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if "Cannot delete" in result["message"] else status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
