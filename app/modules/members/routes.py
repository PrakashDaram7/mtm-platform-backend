"""Members module routes — profile, membership plans, subscriptions."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.core.security import get_current_user, get_db, get_user_from_db, TokenData, user_has_any_role
from app.modules.members.models import MembershipPlan, MemberSubscription
from app.modules.notifications.models import Notification
from app.modules.payments.models import Payment

router = APIRouter(
    prefix="/members",
    tags=["members"],
    responses={404: {"description": "Not found"}}
)


# ─── Profile ───
@router.get("/profile")
async def get_member_profile(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check membership
    subscription = db.query(MemberSubscription).filter(
        MemberSubscription.user_id == user.id,
        MemberSubscription.status == "active"
    ).first()

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
            "membership": {
                "plan_name": subscription.plan.name if subscription and subscription.plan else None,
                "status": subscription.status if subscription else None,
                "start_date": subscription.start_date.isoformat() if subscription and subscription.start_date else None,
                "end_date": subscription.end_date.isoformat() if subscription and subscription.end_date else None,
            } if subscription else None
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


# ─── Membership Plans ───
@router.get("/plans")
async def get_membership_plans(db: Session = Depends(get_db)):
    """Get all active membership plans."""
    plans = db.query(MembershipPlan).filter(MembershipPlan.is_active == True).order_by(MembershipPlan.sort_order).all()
    return {
        "success": True,
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "duration_months": p.duration_months,
                "is_lifetime": p.is_lifetime,
                "features": json.loads(p.features) if p.features else [],
            }
            for p in plans
        ]
    }


@router.post("/subscribe")
async def subscribe_to_plan(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Subscribe to a membership plan."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan_id = request.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id is required")

    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check existing active subscription
    existing = db.query(MemberSubscription).filter(
        MemberSubscription.user_id == user.id,
        MemberSubscription.status == "active"
    ).first()
    if existing:
        return {"success": False, "message": "You already have an active membership"}

    from datetime import datetime, timedelta
    
    # Sprint 1 Implementation defaults to active
    sub = MemberSubscription(
        user_id=user.id,
        plan_id=plan.id,
        status="active",
        amount_paid=plan.price,
    )
    
    if not plan.is_lifetime and plan.duration_months:
        sub.end_date = datetime.utcnow() + timedelta(days=plan.duration_months * 30)

    db.add(sub)
    db.commit()

    return {"success": True, "message": f"Successfully subscribed to {plan.name}"}


# ─── Notifications ───
@router.get("/notifications")
async def get_notifications(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications."""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.user_id
    ).order_by(Notification.created_at.desc()).limit(50).all()

    return {
        "success": True,
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.notification_type,
                "is_read": n.is_read,
                "link": n.link,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
        "unread_count": sum(1 for n in notifications if not n.is_read)
    }


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.user_id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    return {"success": True, "message": "Marked as read"}


# ─── Payments ───
@router.get("/payments")
async def get_user_payments(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's payment history."""
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.user_id
    ).order_by(Payment.created_at.desc()).limit(50).all()

    return {
        "success": True,
        "payments": [
            {
                "id": p.id,
                "amount": p.amount,
                "currency": p.currency,
                "status": p.status,
                "payment_type": p.payment_type,
                "payment_method": p.payment_method,
                "transaction_id": p.transaction_id,
                "description": p.description,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ]
    }


