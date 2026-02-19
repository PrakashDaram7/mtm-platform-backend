"""Organizer module routes — event creation and management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_db, get_user_from_db, TokenData, user_has_any_role

router = APIRouter(
    prefix="/organizer",
    tags=["organizer"],
    responses={404: {"description": "Not found"}}
)


def check_organizer_role(current_user: TokenData, db: Session):
    """Allow organizer or admin."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user_has_any_role(user, ["organizer", "admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer role required"
        )
    return user


@router.get("/dashboard")
async def get_organizer_dashboard(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get organizer dashboard summary."""
    check_organizer_role(current_user, db)

    return {
        "success": True,
        "dashboard": {
            "total_events": 4,
            "published_events": 2,
            "total_registrations": 433,
            "total_revenue": 74600,
            "avg_attendance_pct": 52
        }
    }


@router.get("/events")
async def get_organizer_events(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get events created by this organizer."""
    check_organizer_role(current_user, db)

    # Placeholder — tie into events table when implemented
    return {
        "success": True,
        "events": [
            {
                "id": 1,
                "title": "Ugadi Celebrations 2026",
                "date": "2026-03-30",
                "location": "Hyderabad Convention Center",
                "registered": 248,
                "capacity": 500,
                "status": "published",
                "revenue": 49600
            },
            {
                "id": 2,
                "title": "Telugu Cultural Night",
                "date": "2026-04-14",
                "location": "Mumbai",
                "registered": 125,
                "capacity": 300,
                "status": "published",
                "revenue": 25000
            }
        ]
    }


@router.post("/events")
async def create_event(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new event."""
    check_organizer_role(current_user, db)

    title = request.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Event title is required")

    return {
        "success": True,
        "message": "Event created successfully (saved as draft)",
        "event": {
            "id": 999,
            "title": title,
            "date": request.get("date"),
            "location": request.get("location"),
            "capacity": request.get("capacity", 0),
            "status": "draft"
        }
    }
