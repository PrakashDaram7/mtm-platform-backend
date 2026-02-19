"""Members module routes — profile, events, notifications, payments."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_db, get_user_from_db, TokenData, user_has_any_role

router = APIRouter(
    prefix="/members",
    tags=["members"],
    responses={404: {"description": "Not found"}}
)


def check_member_role(current_user: TokenData, db: Session):
    """Allow member, moderator, organizer, admin."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user_has_any_role(user, ["member", "moderator", "organizer", "admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member role required"
        )
    return user


@router.get("/profile")
async def get_member_profile(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "success": True,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role_name": user.role.role_name if user.role else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
    }


@router.put("/profile")
async def update_member_profile(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if "full_name" in request and request["full_name"]:
        user.full_name = request["full_name"]
    if "phone" in request:
        user.phone = request["phone"]

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Profile updated successfully",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
        }
    }
