"""Events module routes — full CRUD + registration."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.security import get_current_user, get_db, get_user_from_db, TokenData, user_has_any_role
from app.modules.events.services import EventService
from app.modules.events.schemas import EventCreateSchema, EventUpdateSchema, EventRegistrationSchema

router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={404: {"description": "Not found"}}
)


# ─── Public: List published events ───
@router.get("/")
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List events. No auth required for published events."""
    result = EventService.get_all_events(
        db, skip=skip, limit=limit,
        status=status or "published",
        event_type=event_type, city=city, search=search
    )
    return result


# ─── Public: Get single event ───
@router.get("/{event_id}")
async def get_event(event_id: str, db: Session = Depends(get_db)):
    """Get event details."""
    result = EventService.get_event_by_id(db, event_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


# ─── Admin/Organizer: List ALL events (including drafts) ───
@router.get("/manage/all")
async def list_all_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all events for management (admin/organizer)."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "organizer"]):
        raise HTTPException(status_code=403, detail="Admin or Organizer role required")
    result = EventService.get_all_events(db, skip=skip, limit=limit, status=status)
    return result


# ─── Create Event ───
@router.post("/")
async def create_event(
    event_data: EventCreateSchema,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new event (admin/organizer)."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "organizer"]):
        raise HTTPException(status_code=403, detail="Admin or Organizer role required")

    result = EventService.create_event(db, current_user.user_id, event_data.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ─── Update Event ───
@router.put("/{event_id}")
async def update_event(
    event_id: str,
    event_data: EventUpdateSchema,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an event (admin/organizer)."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "organizer"]):
        raise HTTPException(status_code=403, detail="Admin or Organizer role required")

    result = EventService.update_event(db, event_id, event_data.model_dump(exclude_none=True))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ─── Delete Event ───
@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an event (admin only)."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Admin role required")

    result = EventService.delete_event(db, event_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ─── Register for Event ───
@router.post("/register")
async def register_for_event(
    reg_data: EventRegistrationSchema,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register current user for an event."""
    result = EventService.register_for_event(
        db, reg_data.event_id, current_user.user_id, reg_data.notes
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ─── Get registrations for an event (admin/organizer) ───
@router.get("/{event_id}/registrations")
async def get_event_registrations(
    event_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all registrations for an event."""
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_any_role(user, ["admin", "organizer"]):
        raise HTTPException(status_code=403, detail="Admin or Organizer role required")
    return EventService.get_event_registrations(db, event_id)


# ─── Get current user's registrations ───
@router.get("/my/registrations")
async def get_my_registrations(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's event registrations."""
    return EventService.get_user_registrations(db, current_user.user_id)
