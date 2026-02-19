"""Events module schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class EventCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    event_type: str = "other"
    start_date: str  # ISO datetime string
    end_date: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    venue: Optional[str] = None
    is_online: bool = False
    meeting_link: Optional[str] = None
    max_capacity: Optional[int] = None
    fee: float = 0.0
    is_free: bool = True
    members_only: bool = False
    image_url: Optional[str] = None
    status: str = "draft"


class EventUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    venue: Optional[str] = None
    is_online: Optional[bool] = None
    meeting_link: Optional[str] = None
    max_capacity: Optional[int] = None
    fee: Optional[float] = None
    is_free: Optional[bool] = None
    members_only: Optional[bool] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


class EventRegistrationSchema(BaseModel):
    event_id: str
    notes: Optional[str] = None


class EventResponseSchema(BaseModel):
    id: str
    title: str
    description: Optional[str]
    event_type: str
    status: str
    start_date: str
    end_date: Optional[str]
    location: Optional[str]
    city: Optional[str]
    venue: Optional[str]
    is_online: bool
    max_capacity: Optional[int]
    fee: float
    is_free: bool
    members_only: bool
    organizer_name: Optional[str] = None
    registration_count: int = 0
    created_at: Optional[str]

    class Config:
        from_attributes = True
