"""
Members module services — Sprint 2: Full Membership Management (PRD 5.3).

Covers:
  2.1 Membership Plans CRUD  (admin)
  2.2 Registration Workflow  (apply → pending → approve → number issued)
  2.3 Renewal Workflow
  2.4 Self-Service Status Check
  2.5 Admin Overrides (extend / block)
  2.6 CSV/Excel Migration Tool
  Settings: auto_approve_membership toggle
"""

import uuid
import json
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.modules.members.models import Membership, MembershipPlan, AppSettings
from app.modules.auth.models import User, AuditLog, Role


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _generate_membership_number(db: Session) -> str:
    """Generate a human-readable MTM-YYYY-NNNNN membership number."""
    year = datetime.now().year
    count = db.query(Membership).filter(
        func.year(Membership.created_at) == year
    ).count()
    return f"MTM-{year}-{str(count + 1).zfill(5)}"


def _get_setting(db: Session, key: str, default: str = "") -> str:
    """Fetch a platform setting by key."""
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    return setting.value if setting else default


def _set_setting(db: Session, key: str, value: str, description: str = "", updated_by: str = None):
    """Upsert a platform setting."""
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    if setting:
        setting.value = value
        if description:
            setting.description = description
        setting.updated_by = updated_by
    else:
        setting = AppSettings(
            key=key, value=value, description=description, updated_by=updated_by
        )
        db.add(setting)
    db.commit()


def _membership_dict(m: Membership) -> dict:
    """Serialize a Membership ORM object to a dict."""
    return {
        "id": m.id,
        "user_id": m.user_id,
        "membership_number": m.membership_number,
        "membership_type": m.membership_type,
        "status": m.status,
        "plan_id": m.plan_id,
        "plan_name": m.plan.name if m.plan else None,
        "amount_paid": m.amount_paid,
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "expiry_date": m.expiry_date.isoformat() if m.expiry_date else None,
        "admin_notes": m.admin_notes,
        "rejection_reason": m.rejection_reason,
        "block_reason": m.block_reason,
        "renewal_history": m.renewal_history or [],
        "approved_at": m.approved_at.isoformat() if m.approved_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        "user": {
            "id": m.user.id,
            "full_name": m.user.full_name,
            "email": m.user.email,
            "phone": m.user.phone,
        } if m.user else None,
    }


def _log_audit(db: Session, user_id: str, action: str, resource_id: str, details: dict):
    """Write an audit log entry (PRD 3.3)."""
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type="membership",
            resource_id=resource_id,
            details=details,
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        print(f"[WARN] Audit log failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# 2.1 MEMBERSHIP PLAN CRUD  (Admin only)
# ─────────────────────────────────────────────────────────────────────────────

class MembershipPlanService:

    @staticmethod
    def list_plans(db: Session, active_only: bool = False) -> Dict:
        q = db.query(MembershipPlan)
        if active_only:
            q = q.filter(MembershipPlan.is_active == True)
        plans = q.order_by(MembershipPlan.sort_order).all()
        return {
            "success": True,
            "plans": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "membership_type": p.membership_type,
                    "price": p.price,
                    "currency": p.currency,
                    "duration_months": p.duration_months,
                    "is_lifetime": p.is_lifetime,
                    "features": json.loads(p.features) if p.features else [],
                    "is_active": p.is_active,
                    "sort_order": p.sort_order,
                    "member_count": db.query(Membership).filter(
                        Membership.plan_id == p.id, Membership.status == "active"
                    ).count(),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in plans
            ],
        }

    @staticmethod
    def create_plan(db: Session, data: dict, admin_id: str) -> Dict:
        existing = db.query(MembershipPlan).filter(MembershipPlan.name == data.get("name")).first()
        if existing:
            return {"success": False, "message": f"Plan '{data['name']}' already exists"}

        features = data.get("features", [])
        plan = MembershipPlan(
            name=data["name"],
            description=data.get("description"),
            membership_type=data.get("membership_type", "individual"),
            price=data["price"],
            currency=data.get("currency", "MUR"),
            duration_months=None if data.get("is_lifetime") else data.get("duration_months", 12),
            is_lifetime=data.get("is_lifetime", False),
            features=json.dumps(features) if isinstance(features, list) else features,
            sort_order=data.get("sort_order", 0),
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return {"success": True, "message": "Plan created successfully", "plan": {"id": plan.id, "name": plan.name}}

    @staticmethod
    def update_plan(db: Session, plan_id: str, data: dict, admin_id: str) -> Dict:
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id).first()
        if not plan:
            return {"success": False, "message": "Plan not found"}

        for field in ("name", "description", "membership_type", "price", "currency",
                      "duration_months", "is_lifetime", "is_active", "sort_order"):
            if field in data and data[field] is not None:
                setattr(plan, field, data[field])

        if "features" in data:
            feat = data["features"]
            plan.features = json.dumps(feat) if isinstance(feat, list) else feat

        if data.get("is_lifetime"):
            plan.duration_months = None

        db.commit()
        db.refresh(plan)
        return {"success": True, "message": "Plan updated successfully"}

    @staticmethod
    def delete_plan(db: Session, plan_id: str) -> Dict:
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id).first()
        if not plan:
            return {"success": False, "message": "Plan not found"}

        active_count = db.query(Membership).filter(
            Membership.plan_id == plan_id, Membership.status == "active"
        ).count()
        if active_count > 0:
            return {"success": False, "message": f"Cannot delete — {active_count} active member(s) on this plan"}

        db.delete(plan)
        db.commit()
        return {"success": True, "message": "Plan deleted successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# 2.2 REGISTRATION WORKFLOW  (PRD 5.3.2 A)
# ─────────────────────────────────────────────────────────────────────────────

class MembershipService:

    @staticmethod
    def apply_for_membership(db: Session, user_id: str, plan_id: str,
                              membership_type: str = "individual") -> Dict:
        """
        User submits membership application.
        Creates record with status=pending (or active if auto_approve is on).
        PRD 5.3.2 A — steps 1-3.
        """
        # Check existing
        existing = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.status.in_(["pending", "active"])
        ).first()
        if existing:
            return {
                "success": False,
                "message": f"You already have a {existing.status} membership (#{existing.membership_number or 'pending assignment'})",
            }

        plan = db.query(MembershipPlan).filter(
            MembershipPlan.id == plan_id, MembershipPlan.is_active == True
        ).first()
        if not plan:
            return {"success": False, "message": "Membership plan not found or inactive"}

        auto_approve = _get_setting(db, "auto_approve_membership", "false").lower() == "true"

        now = datetime.now(timezone.utc)
        membership = Membership(
            user_id=user_id,
            plan_id=plan_id,
            membership_type=membership_type or plan.membership_type,
            status="pending",
            amount_paid=plan.price,
            renewal_history=[],
        )

        if auto_approve:
            membership.status = "active"
            membership.membership_number = _generate_membership_number(db)
            membership.start_date = now
            if plan.is_lifetime:
                membership.expiry_date = None
            elif plan.duration_months:
                membership.expiry_date = now + timedelta(days=plan.duration_months * 30)
            membership.approved_at = now

        db.add(membership)
        db.commit()
        db.refresh(membership)

        _log_audit(db, user_id, "membership.apply", membership.id, {
            "plan": plan.name, "auto_approved": auto_approve
        })

        return {
            "success": True,
            "message": "Application submitted successfully! Awaiting admin approval." if not auto_approve
                       else f"Membership approved! Your number: {membership.membership_number}",
            "membership": _membership_dict(membership),
        }


    # ─── 2.4 Self-service status check ───────────────────────────────────────

    @staticmethod
    def check_status(db: Session, identifier: str) -> Dict:
        """
        PRD 5.3.2 C — Member checks own status by phone/email/membership number.
        No auth required (public endpoint).
        """
        membership = None

        # Try membership number
        membership = db.query(Membership).filter(
            Membership.membership_number == identifier
        ).first()

        if not membership:
            # Try via user email or phone
            user = db.query(User).filter(
                or_(User.email == identifier, User.phone == identifier)
            ).first()
            if user:
                membership = db.query(Membership).filter(
                    Membership.user_id == user.id
                ).order_by(Membership.created_at.desc()).first()

        if not membership:
            return {"success": False, "message": "No membership record found for the provided details"}

        plan = membership.plan
        result = _membership_dict(membership)

        # Renewal option hint
        can_renew = membership.status in ("active", "expired")
        result["can_renew"] = can_renew

        return {"success": True, "membership": result}


    # ─── 2.3 Renewal Workflow ────────────────────────────────────────────────

    @staticmethod
    def renew_membership(db: Session, user_id: str, plan_id: str = None) -> Dict:
        """
        PRD 5.3.2 B — Renewal: extend expiry, append to renewal_history.
        """
        membership = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.status.in_(["active", "expired"])
        ).order_by(Membership.created_at.desc()).first()

        if not membership:
            return {"success": False, "message": "No membership found to renew. Please apply first."}

        if membership.status == "blocked":
            return {"success": False, "message": "Your membership is blocked. Contact admin."}

        # Use provided plan or stick with current
        if plan_id and plan_id != membership.plan_id:
            new_plan = db.query(MembershipPlan).filter(
                MembershipPlan.id == plan_id, MembershipPlan.is_active == True
            ).first()
            if not new_plan:
                return {"success": False, "message": "Selected plan not found"}
        else:
            new_plan = membership.plan

        now = datetime.now(timezone.utc)
        # Extend from today or from current expiry if still future
        base = membership.expiry_date if membership.expiry_date and membership.expiry_date > now else now

        new_expiry = None
        if not new_plan.is_lifetime and new_plan.duration_months:
            new_expiry = base + timedelta(days=new_plan.duration_months * 30)

        # Append to renewal history
        history = membership.renewal_history or []
        history.append({
            "renewed_at": now.isoformat(),
            "plan": new_plan.name,
            "amount": new_plan.price,
            "new_expiry": new_expiry.isoformat() if new_expiry else "lifetime",
        })

        membership.plan_id = new_plan.id
        membership.membership_type = new_plan.membership_type
        membership.expiry_date = new_expiry
        membership.status = "active"
        membership.renewal_history = history
        membership.amount_paid = new_plan.price

        db.commit()
        db.refresh(membership)

        _log_audit(db, user_id, "membership.renew", membership.id, {
            "plan": new_plan.name, "new_expiry": new_expiry.isoformat() if new_expiry else "lifetime"
        })

        return {
            "success": True,
            "message": f"Membership renewed successfully! New expiry: {new_expiry.strftime('%d %b %Y') if new_expiry else 'Lifetime'}",
            "membership": _membership_dict(membership),
        }


    # ─── 2.5 Admin Overrides ─────────────────────────────────────────────────

    @staticmethod
    def admin_approve(db: Session, membership_id: str, admin_id: str, notes: str = None) -> Dict:
        """Admin approves a pending membership — assigns number + expiry (PRD 5.3.2 A step 3)."""
        m = db.query(Membership).filter(Membership.id == membership_id).first()
        if not m:
            return {"success": False, "message": "Membership not found"}
        if m.status != "pending":
            return {"success": False, "message": f"Membership is already '{m.status}'"}

        now = datetime.now(timezone.utc)
        m.status = "active"
        m.membership_number = _generate_membership_number(db)
        m.start_date = now
        m.approved_by = admin_id
        m.approved_at = now
        if notes:
            m.admin_notes = notes

        plan = m.plan
        if plan:
            if plan.is_lifetime:
                m.expiry_date = None
            elif plan.duration_months:
                m.expiry_date = now + timedelta(days=plan.duration_months * 30)

        db.commit()
        db.refresh(m)
        _log_audit(db, admin_id, "membership.approve", m.id, {"membership_number": m.membership_number})
        return {"success": True, "message": f"Membership approved. Number: {m.membership_number}", "membership": _membership_dict(m)}

    @staticmethod
    def admin_reject(db: Session, membership_id: str, admin_id: str, reason: str) -> Dict:
        """Admin rejects a pending membership."""
        m = db.query(Membership).filter(Membership.id == membership_id).first()
        if not m:
            return {"success": False, "message": "Membership not found"}
        if m.status != "pending":
            return {"success": False, "message": f"Can only reject pending memberships. Current: {m.status}"}

        m.status = "rejected"
        m.rejection_reason = reason
        db.commit()
        _log_audit(db, admin_id, "membership.reject", m.id, {"reason": reason})
        return {"success": True, "message": "Membership rejected"}

    @staticmethod
    def admin_extend(db: Session, membership_id: str, admin_id: str,
                     extend_months: int, reason: str) -> Dict:
        """Admin manually extends expiry (PRD 5.3.2 D)."""
        m = db.query(Membership).filter(Membership.id == membership_id).first()
        if not m:
            return {"success": False, "message": "Membership not found"}

        now = datetime.now(timezone.utc)
        base = m.expiry_date if m.expiry_date and m.expiry_date > now else now
        new_expiry = base + timedelta(days=extend_months * 30)

        history = m.renewal_history or []
        history.append({
            "type": "admin_extension",
            "extended_at": now.isoformat(),
            "extended_by": admin_id,
            "extend_months": extend_months,
            "reason": reason,
            "new_expiry": new_expiry.isoformat(),
        })

        m.expiry_date = new_expiry
        m.status = "active"
        m.renewal_history = history
        if reason:
            m.admin_notes = (m.admin_notes or "") + f"\n[Extension] {reason}"

        db.commit()
        db.refresh(m)
        _log_audit(db, admin_id, "membership.extend", m.id, {"months": extend_months, "reason": reason, "new_expiry": new_expiry.isoformat()})
        return {"success": True, "message": f"Membership extended by {extend_months} month(s). New expiry: {new_expiry.strftime('%d %b %Y')}", "membership": _membership_dict(m)}

    @staticmethod
    def admin_block(db: Session, membership_id: str, admin_id: str, reason: str) -> Dict:
        """Admin blocks a membership (PRD 5.3.2 D)."""
        m = db.query(Membership).filter(Membership.id == membership_id).first()
        if not m:
            return {"success": False, "message": "Membership not found"}

        m.status = "blocked"
        m.block_reason = reason
        db.commit()
        _log_audit(db, admin_id, "membership.block", m.id, {"reason": reason})
        return {"success": True, "message": "Membership blocked"}

    @staticmethod
    def admin_unblock(db: Session, membership_id: str, admin_id: str) -> Dict:
        """Admin unblocks a membership."""
        m = db.query(Membership).filter(Membership.id == membership_id).first()
        if not m:
            return {"success": False, "message": "Membership not found"}
        if m.status != "blocked":
            return {"success": False, "message": "Membership is not blocked"}

        m.status = "active"
        m.block_reason = None
        db.commit()
        _log_audit(db, admin_id, "membership.unblock", m.id, {})
        return {"success": True, "message": "Membership unblocked"}

    @staticmethod
    def admin_send_payment_link(
        db: Session,
        membership_id: str,
        admin_id: str,
        payment_link: str,
        notes: str = ""
    ) -> Dict:
        """
        Admin sends a payment link email to the pending applicant.
        Records the link and notes on the membership for audit purposes.
        Does NOT change the membership status (stays 'pending' until admin approves).
        """
        from app.core.email_service import EmailService

        m = db.query(Membership).filter(Membership.id == membership_id).first()
        if not m:
            return {"success": False, "message": "Membership not found"}
        if m.status not in ("pending", "rejected"):
            return {
                "success": False,
                "message": f"Payment link can only be sent for pending applications. Current status: {m.status}"
            }

        if not payment_link or not payment_link.startswith("http"):
            return {"success": False, "message": "A valid payment URL (starting with http) is required"}

        # Persist link + note on membership
        m.admin_notes = (m.admin_notes or "") + f"\n[Payment Link Sent] {payment_link}"
        if notes:
            m.admin_notes += f" — {notes}"
        db.commit()
        db.refresh(m)

        # Attempt email
        user  = m.user
        plan  = m.plan
        sent  = False
        if user and user.email:
            sent = EmailService.send_payment_link_email(
                recipient_email=user.email,
                member_name=user.full_name or "Member",
                plan_name=plan.name if plan else "Membership",
                amount=float(plan.price) if plan else float(m.amount_paid or 0),
                currency=plan.currency if plan else "MUR",
                payment_link=payment_link,
                notes=notes,
            )

        # In-app notification
        try:
            from app.modules.notifications.models import Notification
            notif = Notification(
                user_id=m.user_id,
                title="Payment Link Ready 💳",
                message=(
                    f"Your membership application has been reviewed. "
                    f"Please complete your payment of {plan.currency if plan else 'MUR'} "
                    f"{float(plan.price if plan else m.amount_paid or 0):,.0f} "
                    f"for the {plan.name if plan else 'membership'} plan."
                ),
                notification_type="payment",
                link=payment_link,
            )
            db.add(notif)
            db.commit()
        except Exception as exc:
            print(f"[WARN] In-app notification failed: {exc}")

        _log_audit(db, admin_id, "membership.payment_link_sent", m.id, {
            "payment_link": payment_link,
            "email_sent": sent,
            "notes": notes,
        })

        return {
            "success": True,
            "message": f"Payment link {'sent via email' if sent else 'recorded (email delivery failed — check SMTP config)'}.",
            "email_sent": sent,
        }


    # ─── List / Detail ────────────────────────────────────────────────────────

    @staticmethod
    def list_memberships(db: Session, status: str = None, skip: int = 0, limit: int = 50,
                          search: str = None) -> Dict:
        """Admin: list all memberships with optional status filter and search."""
        q = db.query(Membership)
        if status:
            q = q.filter(Membership.status == status)
        if search:
            q = q.join(User, Membership.user_id == User.id).filter(
                or_(
                    User.full_name.contains(search),
                    User.email.contains(search),
                    User.phone.contains(search),
                    Membership.membership_number.contains(search),
                )
            )
        total = q.count()
        memberships = q.order_by(Membership.created_at.desc()).offset(skip).limit(limit).all()
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "memberships": [_membership_dict(m) for m in memberships],
        }

    @staticmethod
    def get_membership_stats(db: Session) -> Dict:
        """Quick stats for the admin dashboard."""
        total = db.query(Membership).count()
        active = db.query(Membership).filter(Membership.status == "active").count()
        pending = db.query(Membership).filter(Membership.status == "pending").count()
        expired = db.query(Membership).filter(Membership.status == "expired").count()
        blocked = db.query(Membership).filter(Membership.status == "blocked").count()

        # Expiring in 30 days
        now = datetime.now(timezone.utc)
        expiring_soon = db.query(Membership).filter(
            Membership.status == "active",
            Membership.expiry_date.isnot(None),
            Membership.expiry_date <= now + timedelta(days=30),
        ).count()

        return {
            "success": True,
            "stats": {
                "total": total,
                "active": active,
                "pending": pending,
                "expired": expired,
                "blocked": blocked,
                "expiring_soon": expiring_soon,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2.6 CSV / EXCEL MIGRATION TOOL  (PRD 5.3.3)
# ─────────────────────────────────────────────────────────────────────────────

class MigrationService:

    REQUIRED_FIELDS = {"full_name", "email"}

    @staticmethod
    def preview_csv(csv_content: str, column_map: dict) -> Dict:
        """
        Parse CSV and validate rows — preview before actual import.
        PRD 5.3.3: validate duplicates (email/phone/membership_number), preview summary.
        column_map: { csv_column: model_field }
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        errors = []
        valid_rows = []
        seen_emails = set()
        seen_phones = set()
        seen_numbers = set()

        for i, row in enumerate(rows, start=2):  # row 1 = header
            mapped = {}
            for csv_col, model_field in column_map.items():
                mapped[model_field] = row.get(csv_col, "").strip()

            row_errors = []

            # Required fields
            if not mapped.get("full_name"):
                row_errors.append("full_name is required")
            if not mapped.get("email"):
                row_errors.append("email is required")

            # In-file duplicates
            email = mapped.get("email", "").lower()
            phone = mapped.get("phone", "")
            num   = mapped.get("membership_number", "")

            if email in seen_emails:
                row_errors.append(f"Duplicate email: {email}")
            else:
                seen_emails.add(email)

            if phone and phone in seen_phones:
                row_errors.append(f"Duplicate phone: {phone}")
            elif phone:
                seen_phones.add(phone)

            if num and num in seen_numbers:
                row_errors.append(f"Duplicate membership_number: {num}")
            elif num:
                seen_numbers.add(num)

            if row_errors:
                errors.append({"row": i, "errors": row_errors, "data": mapped})
            else:
                valid_rows.append(mapped)

        return {
            "success": True,
            "total_rows": len(rows),
            "valid_count": len(valid_rows),
            "error_count": len(errors),
            "errors": errors[:50],   # cap preview error list
            "preview_rows": valid_rows[:10],
        }

    @staticmethod
    def import_csv(db: Session, csv_content: str, column_map: dict,
                   admin_id: str, default_plan_id: str = None) -> Dict:
        """
        Import validated CSV rows into the memberships table.
        PRD 5.3.3: import + generate error report.
        """
        member_role = db.query(Role).filter(Role.role_name == "member").first()
        if not member_role:
            return {"success": False, "message": "Member role not found in DB. Run seed script."}

        preview = MigrationService.preview_csv(csv_content, column_map)
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        imported = 0
        skipped = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            mapped = {model_field: row.get(csv_col, "").strip()
                      for csv_col, model_field in column_map.items()}

            email = mapped.get("email", "").lower()
            if not email or not mapped.get("full_name"):
                errors.append({"row": i, "error": "Missing email or full_name", "data": mapped})
                skipped += 1
                continue

            try:
                # Upsert user
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    user = User(
                        full_name=mapped["full_name"],
                        email=email,
                        phone=mapped.get("phone") or None,
                        role_id=member_role.role_id,
                        is_active=True,
                        is_verified=True,
                        address=mapped.get("address"),
                        occupation=mapped.get("occupation"),
                    )
                    db.add(user)
                    db.flush()

                # Skip if active membership already exists
                existing_m = db.query(Membership).filter(
                    Membership.user_id == user.id
                ).first()
                if existing_m:
                    skipped += 1
                    errors.append({"row": i, "error": "Membership already exists", "email": email})
                    continue

                # Parse dates
                start_date = None
                expiry_date = None
                if mapped.get("start_date"):
                    try:
                        start_date = datetime.fromisoformat(mapped["start_date"])
                    except:
                        pass
                if mapped.get("expiry_date"):
                    try:
                        expiry_date = datetime.fromisoformat(mapped["expiry_date"])
                    except:
                        pass

                status = mapped.get("status", "active")
                if status not in ("active", "expired", "pending", "blocked"):
                    status = "active"

                membership = Membership(
                    user_id=user.id,
                    plan_id=default_plan_id,
                    membership_number=mapped.get("membership_number") or _generate_membership_number(db),
                    membership_type=mapped.get("membership_type", "individual"),
                    status=status,
                    start_date=start_date or datetime.now(timezone.utc),
                    expiry_date=expiry_date,
                    amount_paid=float(mapped.get("amount_paid", 0) or 0),
                    admin_notes=f"Migrated via CSV import by admin",
                    approved_by=admin_id,
                    approved_at=datetime.now(timezone.utc),
                    renewal_history=[],
                )
                db.add(membership)
                db.flush()
                imported += 1

            except Exception as exc:
                db.rollback()
                errors.append({"row": i, "error": str(exc), "email": email})
                skipped += 1
                continue

        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            return {"success": False, "message": f"Commit failed: {exc}"}

        _log_audit(db, admin_id, "membership.csv_import", "bulk", {
            "imported": imported, "skipped": skipped
        })

        return {
            "success": True,
            "message": f"Import complete. {imported} imported, {skipped} skipped.",
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
        }


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class SettingsService:

    DEFAULT_SETTINGS = [
        ("auto_approve_membership", "false", "Auto-approve new membership applications without admin review"),
        ("membership_renewal_reminder_days", "60,30,7,0,7", "Comma-separated days before/after expiry to send renewal reminders"),
        ("platform_name", "Mauritius Telugu Mahasabha", "Platform display name"),
        ("contact_email", "info@mtm.mu", "Contact email shown to members"),
        ("currency", "MUR", "Default currency for memberships"),
    ]

    @staticmethod
    def initialize_defaults(db: Session):
        """Seed default settings if they don't exist."""
        for key, value, desc in SettingsService.DEFAULT_SETTINGS:
            existing = db.query(AppSettings).filter(AppSettings.key == key).first()
            if not existing:
                db.add(AppSettings(key=key, value=value, description=desc))
        db.commit()

    @staticmethod
    def get_all(db: Session) -> Dict:
        settings = db.query(AppSettings).all()
        return {
            "success": True,
            "settings": [
                {
                    "id": s.id,
                    "key": s.key,
                    "value": s.value,
                    "description": s.description,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in settings
            ],
        }

    @staticmethod
    def update(db: Session, key: str, value: str, admin_id: str) -> Dict:
        _set_setting(db, key, value, updated_by=admin_id)
        _log_audit(db, admin_id, "settings.update", key, {"value": value})
        return {"success": True, "message": f"Setting '{key}' updated to '{value}'"}
