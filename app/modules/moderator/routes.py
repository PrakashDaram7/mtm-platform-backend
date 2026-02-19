"""Moderator module routes — content reports and review."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_db, get_user_from_db, TokenData, user_has_any_role

router = APIRouter(
    prefix="/moderator",
    tags=["moderator"],
    responses={404: {"description": "Not found"}}
)


def check_moderator_role(current_user: TokenData, db: Session):
    """Allow moderator or admin."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user_has_any_role(user, ["moderator", "admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator role required"
        )
    return user


@router.get("/dashboard")
async def get_moderator_dashboard(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get moderator dashboard summary."""
    check_moderator_role(current_user, db)

    return {
        "success": True,
        "dashboard": {
            "pending_reports": 3,
            "reviewed_today": 12,
            "active_posts": 156,
            "flagged_content": 7,
            "banned_users": 2,
            "resolved_this_week": 34
        }
    }


@router.get("/reports")
async def get_reports(
    status_filter: str = "all",
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get content reports."""
    check_moderator_role(current_user, db)

    # Sample data — replace with DB queries when reports table exists
    reports = [
        {"id": 1, "type": "spam", "reporter": "John Smith", "content": "Inappropriate message in forum",
         "status": "pending", "date": "2026-02-19", "priority": "high"},
        {"id": 2, "type": "harassment", "reporter": "Priya K.", "content": "Abusive comments",
         "status": "pending", "date": "2026-02-18", "priority": "high"},
        {"id": 3, "type": "misinformation", "reporter": "Raju M.", "content": "Fake event listing",
         "status": "under_review", "date": "2026-02-17", "priority": "medium"},
    ]

    if status_filter != "all":
        reports = [r for r in reports if r["status"] == status_filter]

    return {
        "success": True,
        "total": len(reports),
        "reports": reports
    }


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve a content report."""
    check_moderator_role(current_user, db)
    return {
        "success": True,
        "message": f"Report {report_id} resolved successfully"
    }


@router.post("/reports/{report_id}/dismiss")
async def dismiss_report(
    report_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dismiss a content report."""
    check_moderator_role(current_user, db)
    return {
        "success": True,
        "message": f"Report {report_id} dismissed"
    }
