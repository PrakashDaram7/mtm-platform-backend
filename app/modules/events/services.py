"""Events module services."""

from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.modules.events.models import Event, EventRegistration
from app.modules.auth.models import User


class EventService:
    """Service for event management operations."""

    @staticmethod
    def get_all_events(db: Session, skip: int = 0, limit: int = 20,
                       status: str = None, event_type: str = None,
                       city: str = None, search: str = None) -> Dict:
        """Get events with filtering and pagination."""
        try:
            query = db.query(Event)

            if status:
                query = query.filter(Event.status == status)
            if event_type:
                query = query.filter(Event.event_type == event_type)
            if city:
                query = query.filter(Event.city.ilike(f"%{city}%"))
            if search:
                query = query.filter(
                    or_(Event.title.ilike(f"%{search}%"), Event.description.ilike(f"%{search}%"))
                )

            total = query.count()
            events = query.order_by(Event.start_date.desc()).offset(skip).limit(limit).all()

            return {
                "success": True,
                "total": total,
                "events": [EventService._event_to_dict(e, db) for e in events]
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}", "total": 0, "events": []}

    @staticmethod
    def get_event_by_id(db: Session, event_id: str) -> Dict:
        """Get a single event by ID."""
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return {"success": False, "message": "Event not found", "event": None}
            return {"success": True, "event": EventService._event_to_dict(event, db)}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}", "event": None}

    @staticmethod
    def create_event(db: Session, organizer_id: str, data: dict) -> Dict:
        """Create a new event."""
        try:
            event = Event(
                title=data["title"],
                description=data.get("description"),
                event_type=data.get("event_type", "other"),
                status=data.get("status", "draft"),
                start_date=datetime.fromisoformat(data["start_date"]),
                end_date=datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None,
                location=data.get("location"),
                city=data.get("city"),
                venue=data.get("venue"),
                is_online=data.get("is_online", False),
                meeting_link=data.get("meeting_link"),
                max_capacity=data.get("max_capacity"),
                fee=data.get("fee", 0.0),
                is_free=data.get("is_free", True),
                members_only=data.get("members_only", False),
                image_url=data.get("image_url"),
                organizer_id=organizer_id,
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            return {"success": True, "message": "Event created successfully", "event": EventService._event_to_dict(event, db)}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Error creating event: {str(e)}", "event": None}

    @staticmethod
    def update_event(db: Session, event_id: str, data: dict) -> Dict:
        """Update an event."""
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return {"success": False, "message": "Event not found"}

            for field in ["title", "description", "event_type", "status", "location",
                          "city", "venue", "is_online", "meeting_link", "max_capacity",
                          "fee", "is_free", "members_only", "image_url"]:
                if field in data and data[field] is not None:
                    setattr(event, field, data[field])

            if "start_date" in data and data["start_date"]:
                event.start_date = datetime.fromisoformat(data["start_date"])
            if "end_date" in data and data["end_date"]:
                event.end_date = datetime.fromisoformat(data["end_date"])

            db.commit()
            db.refresh(event)
            return {"success": True, "message": "Event updated", "event": EventService._event_to_dict(event, db)}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Error: {str(e)}"}

    @staticmethod
    def delete_event(db: Session, event_id: str) -> Dict:
        """Delete an event."""
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return {"success": False, "message": "Event not found"}
            db.delete(event)
            db.commit()
            return {"success": True, "message": "Event deleted"}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Error: {str(e)}"}

    @staticmethod
    def register_for_event(db: Session, event_id: str, user_id: str, notes: str = None) -> Dict:
        """Register a user for an event."""
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return {"success": False, "message": "Event not found"}
            if event.status != "published":
                return {"success": False, "message": "Event is not open for registration"}

            existing = db.query(EventRegistration).filter(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user_id
            ).first()
            if existing:
                return {"success": False, "message": "Already registered"}

            if event.max_capacity:
                current_count = db.query(EventRegistration).filter(
                    EventRegistration.event_id == event_id,
                    EventRegistration.status.in_(["registered", "confirmed"])
                ).count()
                if current_count >= event.max_capacity:
                    return {"success": False, "message": "Event is full"}

            reg = EventRegistration(
                event_id=event_id,
                user_id=user_id,
                status="registered",
                payment_status="paid" if event.is_free else "pending",
                amount_paid=0.0 if event.is_free else event.fee,
                notes=notes,
            )
            db.add(reg)
            db.commit()
            db.refresh(reg)
            return {"success": True, "message": "Registered successfully", "registration_id": reg.id}
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Error: {str(e)}"}

    @staticmethod
    def get_event_registrations(db: Session, event_id: str) -> Dict:
        """Get all registrations for an event."""
        try:
            regs = db.query(EventRegistration).filter(EventRegistration.event_id == event_id).all()
            return {
                "success": True,
                "registrations": [
                    {
                        "id": r.id,
                        "user_id": r.user_id,
                        "user_name": r.user.full_name if r.user else "Unknown",
                        "user_email": r.user.email if r.user else None,
                        "status": r.status,
                        "payment_status": r.payment_status,
                        "amount_paid": r.amount_paid,
                        "registered_at": r.registered_at.isoformat() if r.registered_at else None,
                    }
                    for r in regs
                ]
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}", "registrations": []}

    @staticmethod
    def get_user_registrations(db: Session, user_id: str) -> Dict:
        """Get all event registrations for a user."""
        try:
            regs = db.query(EventRegistration).filter(EventRegistration.user_id == user_id).all()
            return {
                "success": True,
                "registrations": [
                    {
                        "id": r.id,
                        "event_id": r.event_id,
                        "event_title": r.event.title if r.event else "Unknown",
                        "event_date": r.event.start_date.isoformat() if r.event and r.event.start_date else None,
                        "status": r.status,
                        "payment_status": r.payment_status,
                        "registered_at": r.registered_at.isoformat() if r.registered_at else None,
                    }
                    for r in regs
                ]
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}", "registrations": []}

    @staticmethod
    def _event_to_dict(event: Event, db: Session) -> dict:
        """Convert event model to dictionary."""
        reg_count = db.query(EventRegistration).filter(
            EventRegistration.event_id == event.id,
            EventRegistration.status.in_(["registered", "confirmed", "attended"])
        ).count()

        return {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "event_type": event.event_type,
            "status": event.status,
            "start_date": event.start_date.isoformat() if event.start_date else None,
            "end_date": event.end_date.isoformat() if event.end_date else None,
            "location": event.location,
            "city": event.city,
            "venue": event.venue,
            "is_online": event.is_online,
            "meeting_link": event.meeting_link,
            "max_capacity": event.max_capacity,
            "fee": event.fee,
            "is_free": event.is_free,
            "members_only": event.members_only,
            "image_url": event.image_url,
            "organizer_id": event.organizer_id,
            "organizer_name": event.organizer.full_name if event.organizer else None,
            "registration_count": reg_count,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None,
        }
