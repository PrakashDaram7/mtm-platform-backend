"""
Members module routes — Sprint 2: Full Membership Management (PRD 5.3).

Endpoints:
  Public:
    GET  /members/plans                  → list active plans
    GET  /members/status/{identifier}    → self-service status check (no auth)
    POST /members/apply                  → submit application (auth required)
    POST /members/renew                  → renew membership (auth required)
    GET  /members/my-membership          → get own membership

  Admin:
    GET    /members/admin/all            → list all memberships (filterable)
    GET    /members/admin/stats          → quick stats
    POST   /members/admin/{id}/approve   → approve pending
    POST   /members/admin/{id}/reject    → reject pending
    POST   /members/admin/{id}/extend    → extend expiry
    POST   /members/admin/{id}/block     → block
    POST   /members/admin/{id}/unblock   → unblock

  Plans (admin):
    POST   /members/plans                → create plan
    PUT    /members/plans/{id}           → update plan
    DELETE /members/plans/{id}           → delete plan

  CSV Migration (admin):
    POST   /members/admin/import/preview → preview before import
    POST   /members/admin/import/execute → execute import

  Settings:
    GET    /members/admin/settings       → get all settings
    PUT    /members/admin/settings/{key} → update a setting
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.core.security import get_current_user, get_db, get_user_from_db, TokenData, user_has_role, user_has_any_role
from app.modules.members.models import MembershipPlan, Membership, AppSettings
from app.modules.members.services import (
    MembershipPlanService, MembershipService, MigrationService, SettingsService
)

router = APIRouter(
    prefix="/members",
    tags=["members"],
    responses={404: {"description": "Not found"}}
)


# ─── Guards ──────────────────────────────────────────────────────────────────

def _require_admin(current_user: TokenData, db: Session):
    user = get_user_from_db(current_user.user_id, db)
    if not user or not user_has_role(user, "admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user

def _require_member_or_admin(current_user: TokenData, db: Session):
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC — PLANS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List membership plans (public — shown on application wizard)."""
    return MembershipPlanService.list_plans(db, active_only=active_only)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC — SELF-SERVICE STATUS CHECK  (PRD 5.3.2 C)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status/{identifier}")
async def check_membership_status(
    identifier: str,
    db: Session = Depends(get_db)
):
    """
    Public self-service status check.
    identifier can be: membership_number | email | phone
    """
    return MembershipService.check_status(db, identifier)


# ─────────────────────────────────────────────────────────────────────────────
# MEMBER — OWN MEMBERSHIP
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/my-membership")
async def get_my_membership(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's own membership details."""
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.user_id
    ).order_by(Membership.created_at.desc()).first()

    if not membership:
        return {"success": True, "membership": None, "message": "No membership found. Please apply."}

    from app.modules.members.services import _membership_dict
    return {"success": True, "membership": _membership_dict(membership)}


@router.post("/apply")
async def apply_for_membership(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a membership application (PRD 5.3.2 A).
    Body: { plan_id, membership_type? }
    """
    plan_id = request.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id is required")

    result = MembershipService.apply_for_membership(
        db,
        user_id=current_user.user_id,
        plan_id=plan_id,
        membership_type=request.get("membership_type", "individual")
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/renew")
async def renew_membership(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Renew existing membership (PRD 5.3.2 B).
    Body: { plan_id? }  — optional plan change
    """
    result = MembershipService.renew_membership(
        db,
        user_id=current_user.user_id,
        plan_id=request.get("plan_id")
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# MEMBER PROFILE  (kept from Sprint 1)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_member_profile(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile."""
    user = get_user_from_db(current_user.user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    membership = db.query(Membership).filter(
        Membership.user_id == user.id
    ).order_by(Membership.created_at.desc()).first()

    from app.modules.members.services import _membership_dict
    return {
        "success": True,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "address": user.address,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "occupation": user.occupation,
            "preferred_language": user.preferred_language,
            "consent_whatsapp": user.consent_whatsapp,
            "consent_email": user.consent_email,
            "consent_emergency": user.consent_emergency,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role_name": user.role.role_name if user.role else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "membership": _membership_dict(membership) if membership else None,
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

    updatable = ["full_name", "phone", "address", "occupation", "preferred_language",
                 "consent_whatsapp", "consent_email", "consent_emergency"]
    for field in updatable:
        if field in request:
            setattr(user, field, request[field])

    if "date_of_birth" in request and request["date_of_birth"]:
        from datetime import date
        try:
            user.date_of_birth = date.fromisoformat(request["date_of_birth"])
        except:
            pass

    db.commit()
    db.refresh(user)
    return {"success": True, "message": "Profile updated successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# MEMBER — NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/notifications")
async def get_my_notifications(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user."""
    try:
        from app.modules.notifications.models import Notification
        notifs = db.query(Notification).filter(
            Notification.user_id == current_user.user_id
        ).order_by(Notification.created_at.desc()).limit(50).all()
        return {
            "success": True,
            "notifications": [
                {
                    "id": n.id,
                    "type": getattr(n, "notification_type", "general"),
                    "title": getattr(n, "title", None),
                    "message": n.message,
                    "is_read": getattr(n, "is_read", False),
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifs
            ]
        }
    except Exception:
        return {"success": True, "notifications": []}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    try:
        from app.modules.notifications.models import Notification
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.user_id
        ).first()
        if notif:
            notif.is_read = True
            db.commit()
        return {"success": True, "message": "Marked as read"}
    except Exception:
        return {"success": True, "message": "OK"}


# ─────────────────────────────────────────────────────────────────────────────
# MEMBER — PAYMENT HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/payments")
async def get_my_payments(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment history for the current user."""
    try:
        from app.modules.payments.models import Payment
        pays = db.query(Payment).filter(
            Payment.user_id == current_user.user_id
        ).order_by(Payment.created_at.desc()).limit(50).all()
        return {
            "success": True,
            "payments": [
                {
                    "id": p.id,
                    "amount": float(getattr(p, "amount", 0)),
                    "description": getattr(p, "description", None) or getattr(p, "payment_type", "—"),
                    "status": getattr(p, "status", "completed"),
                    "payment_type": getattr(p, "payment_type", None),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in pays
            ]
        }
    except Exception:
        return {"success": True, "payments": []}


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — MEMBERSHIP PLANS CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/admin/plans")

async def admin_list_plans(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: list all plans (including inactive)."""
    _require_admin(current_user, db)
    return MembershipPlanService.list_plans(db, active_only=False)


@router.post("/admin/plans")
async def admin_create_plan(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: create a new membership plan."""
    _require_admin(current_user, db)
    if not request.get("name") or request.get("price") is None:
        raise HTTPException(status_code=400, detail="name and price are required")
    result = MembershipPlanService.create_plan(db, request, current_user.user_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.put("/admin/plans/{plan_id}")
async def admin_update_plan(
    plan_id: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: update a membership plan."""
    _require_admin(current_user, db)
    result = MembershipPlanService.update_plan(db, plan_id, request, current_user.user_id)
    if not result["success"]:
        raise HTTPException(status_code=404 if "not found" in result["message"].lower() else 400,
                            detail=result["message"])
    return result


@router.delete("/admin/plans/{plan_id}")
async def admin_delete_plan(
    plan_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: delete a membership plan."""
    _require_admin(current_user, db)
    result = MembershipPlanService.delete_plan(db, plan_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — MEMBERSHIP MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/admin/all")
async def admin_list_memberships(
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: list all memberships with optional status filter and search."""
    _require_admin(current_user, db)
    return MembershipService.list_memberships(db, status=status, skip=skip, limit=limit, search=search)


@router.get("/admin/stats")
async def admin_membership_stats(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: quick membership statistics."""
    _require_admin(current_user, db)
    return MembershipService.get_membership_stats(db)


@router.post("/admin/{membership_id}/approve")
async def admin_approve_membership(
    membership_id: str,
    request: dict = {},
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: approve a pending membership application."""
    _require_admin(current_user, db)
    result = MembershipService.admin_approve(
        db, membership_id, current_user.user_id, request.get("notes")
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/admin/{membership_id}/reject")
async def admin_reject_membership(
    membership_id: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: reject a pending membership application."""
    _require_admin(current_user, db)
    if not request.get("reason"):
        raise HTTPException(status_code=400, detail="reason is required")
    result = MembershipService.admin_reject(
        db, membership_id, current_user.user_id, request["reason"]
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/admin/{membership_id}/extend")
async def admin_extend_membership(
    membership_id: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: manually extend membership expiry by N months."""
    _require_admin(current_user, db)
    months = request.get("extend_months")
    if not months or int(months) < 1:
        raise HTTPException(status_code=400, detail="extend_months must be ≥ 1")
    result = MembershipService.admin_extend(
        db, membership_id, current_user.user_id,
        int(months), request.get("reason", "Admin extension")
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/admin/{membership_id}/block")
async def admin_block_membership(
    membership_id: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: block a membership."""
    _require_admin(current_user, db)
    if not request.get("reason"):
        raise HTTPException(status_code=400, detail="reason is required")
    result = MembershipService.admin_block(
        db, membership_id, current_user.user_id, request["reason"]
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/admin/{membership_id}/unblock")
async def admin_unblock_membership(
    membership_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: unblock a membership."""
    _require_admin(current_user, db)
    result = MembershipService.admin_unblock(db, membership_id, current_user.user_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/admin/{membership_id}/send-payment-link")
async def admin_send_payment_link(
    membership_id: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin: send a payment link email to a pending applicant.
    Body: { payment_link: "https://...", notes?: "..." }
    """
    _require_admin(current_user, db)
    payment_link = request.get("payment_link", "").strip()
    if not payment_link:
        raise HTTPException(status_code=400, detail="payment_link is required")
    result = MembershipService.admin_send_payment_link(
        db,
        membership_id=membership_id,
        admin_id=current_user.user_id,
        payment_link=payment_link,
        notes=request.get("notes", ""),
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — CSV MIGRATION  (PRD 5.3.3)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/admin/import/preview")
async def import_preview(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview CSV import before executing.
    Body: { csv_content: "...", column_map: { "CSV Col": "model_field" } }
    """
    _require_admin(current_user, db)
    csv_content = request.get("csv_content", "")
    column_map  = request.get("column_map", {})
    if not csv_content:
        raise HTTPException(status_code=400, detail="csv_content is required")
    return MigrationService.preview_csv(csv_content, column_map)


@router.post("/admin/import/execute")
async def import_execute(
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute CSV import.
    Body: { csv_content, column_map, default_plan_id? }
    """
    _require_admin(current_user, db)
    csv_content = request.get("csv_content", "")
    column_map  = request.get("column_map", {})
    if not csv_content:
        raise HTTPException(status_code=400, detail="csv_content is required")
    result = MigrationService.import_csv(
        db, csv_content, column_map,
        admin_id=current_user.user_id,
        default_plan_id=request.get("default_plan_id")
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — SETTINGS  (auto_approve toggle + others)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/admin/settings")
async def get_platform_settings(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: get all platform settings."""
    _require_admin(current_user, db)
    SettingsService.initialize_defaults(db)  # ensure defaults exist
    return SettingsService.get_all(db)


@router.put("/admin/settings/{key}")
async def update_platform_setting(
    key: str,
    request: dict,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin: update a platform setting.
    Body: { value: "..." }
    """
    _require_admin(current_user, db)
    value = request.get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="value is required")
    return SettingsService.update(db, key, str(value), current_user.user_id)


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS (Sprint 1 carried over)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications."""
    from app.modules.notifications.models import Notification
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.user_id
    ).order_by(Notification.created_at.desc()).limit(50).all()

    return {
        "success": True,
        "notifications": [
            {
                "id": n.id, "title": n.title, "message": n.message,
                "type": n.notification_type, "is_read": n.is_read,
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
    from app.modules.notifications.models import Notification
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.user_id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    return {"success": True, "message": "Marked as read"}


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENTS (Sprint 1 carried over)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/payments")
async def get_user_payments(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's payment history."""
    from app.modules.payments.models import Payment
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.user_id
    ).order_by(Payment.created_at.desc()).limit(50).all()

    return {
        "success": True,
        "payments": [
            {
                "id": p.id, "amount": p.amount, "currency": p.currency,
                "status": p.status, "payment_type": p.payment_type,
                "payment_method": p.payment_method, "transaction_id": p.transaction_id,
                "description": p.description,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ]
    }
