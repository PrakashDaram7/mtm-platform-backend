"""
Seed script — aligned with PRD Section 3.
Populates roles, permissions, and sample users for the MTM Platform.

PRD Roles (Section 3.1):
  admin, finance_admin, event_manager, committee_member,
  moderator, member, family_member, volunteer
"""

import uuid
from app.core.database import SessionLocal

# Import models directly (skip __init__.py)
import app.modules.auth.models as auth_models
Role = auth_models.Role
User = auth_models.User
Permission = auth_models.Permission


# =============================================================================
# 1) ROLES — PRD Section 3.1
# =============================================================================
def seed_roles(session):
    """Insert the 8 PRD-defined roles."""
    print("Seeding roles (PRD 3.1)...")

    roles_data = [
        {"role_name": "admin",            "description": "Super Admin — full system access (PRD 3.1.6)"},
        {"role_name": "finance_admin",    "description": "Finance Admin — payments, receipts, donation reports (PRD 3.1.7)"},
        {"role_name": "event_manager",    "description": "Event Manager — events + volunteer management (PRD 3.1.8)"},
        {"role_name": "committee_member", "description": "Committee Member — announcements, events, limited reports (PRD 3.1.5)"},
        {"role_name": "moderator",        "description": "Moderator — forum moderation, content flags (PRD 3.1.9)"},
        {"role_name": "member",           "description": "Member — registered + paid individual (PRD 3.1.2)"},
        {"role_name": "family_member",    "description": "Family Member — linked to a Member profile (PRD 3.1.3)"},
        {"role_name": "volunteer",        "description": "Volunteer — applied + approved, member or non-member (PRD 3.1.4)"},
    ]

    try:
        for role_data in roles_data:
            existing = session.query(Role).filter(Role.role_name == role_data["role_name"]).first()
            if not existing:
                new_role = Role(
                    role_id=str(uuid.uuid4()),
                    role_name=role_data["role_name"],
                    description=role_data["description"],
                    is_active=True
                )
                session.add(new_role)
                session.flush()
                print(f"  ✅ Added role: {role_data['role_name']}")
            else:
                print(f"  ℹ️  Role already exists: {role_data['role_name']}")
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error seeding roles: {e}")
        raise


# =============================================================================
# 2) PERMISSIONS — PRD Section 3.2
# =============================================================================
def seed_permissions(session):
    """Insert comprehensive permissions per PRD Section 3.2."""
    print("\nSeeding permissions (PRD 3.2)...")

    role_map = {}
    for role in session.query(Role).all():
        role_map[role.role_name] = role.role_id

    # Permission definitions: (role, permission_name, resource, action)
    perms = [
        # ─── Admin: FULL ACCESS ───
        ("admin", "admin.full_access",          "admin",        "full_access"),
        ("admin", "users.create",               "users",        "create"),
        ("admin", "users.read",                 "users",        "read"),
        ("admin", "users.update",               "users",        "update"),
        ("admin", "users.delete",               "users",        "delete"),
        ("admin", "membership.create",          "membership",   "create"),
        ("admin", "membership.read",            "membership",   "read"),
        ("admin", "membership.update",          "membership",   "update"),
        ("admin", "membership.delete",          "membership",   "delete"),
        ("admin", "membership.override",        "membership",   "override"),
        ("admin", "events.create",              "events",       "create"),
        ("admin", "events.read",                "events",       "read"),
        ("admin", "events.update",              "events",       "update"),
        ("admin", "events.delete",              "events",       "delete"),
        ("admin", "volunteers.create",          "volunteers",   "create"),
        ("admin", "volunteers.read",            "volunteers",   "read"),
        ("admin", "volunteers.update",          "volunteers",   "update"),
        ("admin", "volunteers.delete",          "volunteers",   "delete"),
        ("admin", "payments.read",              "payments",     "read"),
        ("admin", "payments.create",            "payments",     "create"),
        ("admin", "payments.refund",            "payments",     "refund"),
        ("admin", "donations.read",             "donations",    "read"),
        ("admin", "donations.create",           "donations",    "create"),
        ("admin", "content.create",             "content",      "create"),
        ("admin", "content.read",               "content",      "read"),
        ("admin", "content.update",             "content",      "update"),
        ("admin", "content.delete",             "content",      "delete"),
        ("admin", "announcements.create",       "announcements","create"),
        ("admin", "announcements.read",         "announcements","read"),
        ("admin", "announcements.update",       "announcements","update"),
        ("admin", "announcements.delete",       "announcements","delete"),
        ("admin", "audit_logs.read",            "audit_logs",   "read"),
        ("admin", "reports.read",               "reports",      "read"),
        ("admin", "settings.read",              "settings",     "read"),
        ("admin", "settings.update",            "settings",     "update"),
        ("admin", "tickets.read",               "tickets",      "read"),
        ("admin", "tickets.update",             "tickets",      "update"),
        ("admin", "documents.create",           "documents",    "create"),
        ("admin", "documents.read",             "documents",    "read"),
        ("admin", "notifications.create",       "notifications","create"),
        ("admin", "notifications.read",         "notifications","read"),

        # ─── Finance Admin: payments, receipts, donation reports ───
        ("finance_admin", "payments.read",      "payments",     "read"),
        ("finance_admin", "payments.create",    "payments",     "create"),
        ("finance_admin", "payments.refund",    "payments",     "refund"),
        ("finance_admin", "donations.read",     "donations",    "read"),
        ("finance_admin", "donations.create",   "donations",    "create"),
        ("finance_admin", "receipts.create",    "receipts",     "create"),
        ("finance_admin", "receipts.read",      "receipts",     "read"),
        ("finance_admin", "reports.read",       "reports",      "read"),
        ("finance_admin", "membership.read",    "membership",   "read"),

        # ─── Event Manager: events + volunteers ───
        ("event_manager", "events.create",      "events",       "create"),
        ("event_manager", "events.read",        "events",       "read"),
        ("event_manager", "events.update",      "events",       "update"),
        ("event_manager", "events.delete",      "events",       "delete"),
        ("event_manager", "volunteers.create",  "volunteers",   "create"),
        ("event_manager", "volunteers.read",    "volunteers",   "read"),
        ("event_manager", "volunteers.update",  "volunteers",   "update"),
        ("event_manager", "volunteers.delete",  "volunteers",   "delete"),
        ("event_manager", "reports.read",       "reports",      "read"),

        # ─── Committee Member: announcements, events, limited reports ───
        ("committee_member", "announcements.create",  "announcements", "create"),
        ("committee_member", "announcements.read",    "announcements", "read"),
        ("committee_member", "announcements.update",  "announcements", "update"),
        ("committee_member", "events.create",         "events",        "create"),
        ("committee_member", "events.read",           "events",        "read"),
        ("committee_member", "events.update",         "events",        "update"),
        ("committee_member", "reports.read",           "reports",       "read"),

        # ─── Moderator: remove/flag posts and users ───
        ("moderator", "content.moderate",       "content",      "moderate"),
        ("moderator", "content.read",           "content",      "read"),
        ("moderator", "content.delete",         "content",      "delete"),
        ("moderator", "users.read",             "users",        "read"),
        ("moderator", "users.flag",             "users",        "flag"),
        ("moderator", "announcements.read",     "announcements","read"),

        # ─── Member: own profile, renewal, event registration ───
        ("member", "profile.read",              "profile",      "read"),
        ("member", "profile.update",            "profile",      "update"),
        ("member", "membership.read",           "membership",   "read"),
        ("member", "membership.renew",          "membership",   "renew"),
        ("member", "events.read",               "events",       "read"),
        ("member", "events.register",           "events",       "register"),
        ("member", "payments.read",             "payments",     "read"),
        ("member", "payments.create",           "payments",     "create"),
        ("member", "family.create",             "family",       "create"),
        ("member", "family.read",               "family",       "read"),
        ("member", "family.update",             "family",       "update"),
        ("member", "family.delete",             "family",       "delete"),
        ("member", "tickets.create",            "tickets",      "create"),
        ("member", "tickets.read",              "tickets",      "read"),
        ("member", "notifications.read",        "notifications","read"),

        # ─── Family Member: limited access ───
        ("family_member", "profile.read",       "profile",      "read"),
        ("family_member", "profile.update",     "profile",      "update"),
        ("family_member", "events.read",        "events",       "read"),
        ("family_member", "events.register",    "events",       "register"),

        # ─── Volunteer: limited access + volunteering ───
        ("volunteer", "profile.read",           "profile",      "read"),
        ("volunteer", "profile.update",         "profile",      "update"),
        ("volunteer", "events.read",            "events",       "read"),
        ("volunteer", "events.register",        "events",       "register"),
        ("volunteer", "volunteers.read",        "volunteers",   "read"),
        ("volunteer", "volunteers.update",      "volunteers",   "update"),
    ]

    try:
        for role_name, perm_name, resource, action in perms:
            rid = role_map.get(role_name)
            if not rid:
                print(f"  ⚠️  Role '{role_name}' not found, skipping permission '{perm_name}'")
                continue

            # Check if this exact role-permission combo exists
            existing = session.query(Permission).filter(
                Permission.role_id == rid,
                Permission.resource == resource,
                Permission.action == action,
            ).first()

            if not existing:
                new_perm = Permission(
                    permission_id=str(uuid.uuid4()),
                    permission_name=perm_name,
                    resource=resource,
                    action=action,
                    role_id=rid,
                )
                session.add(new_perm)
                print(f"  ✅ {role_name}: {perm_name}")

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error seeding permissions: {e}")
        raise


# =============================================================================
# 3) SAMPLE USERS
# =============================================================================
def seed_users(session):
    """Insert sample users for each PRD role."""
    print("\nSeeding users...")

    role_map = {}
    for role in session.query(Role).all():
        role_map[role.role_name] = role.role_id

    users_data = [
        {
            "full_name": "Admin User",
            "email": "admin@mtm.com",
            "phone": "+2301000001",
            "role": "admin",
            "is_verified": True,
        },
        {
            "full_name": "Finance Manager",
            "email": "finance@mtm.com",
            "phone": "+2301000002",
            "role": "finance_admin",
            "is_verified": True,
        },
        {
            "full_name": "Event Coordinator",
            "email": "events@mtm.com",
            "phone": "+2301000003",
            "role": "event_manager",
            "is_verified": True,
        },
        {
            "full_name": "Committee Leader",
            "email": "committee@mtm.com",
            "phone": "+2301000004",
            "role": "committee_member",
            "is_verified": True,
        },
        {
            "full_name": "Forum Moderator",
            "email": "moderator@mtm.com",
            "phone": "+2301000005",
            "role": "moderator",
            "is_verified": True,
        },
        {
            "full_name": "Ravi Kumar",
            "email": "member@mtm.com",
            "phone": "+2301000006",
            "role": "member",
            "is_verified": True,
        },
        {
            "full_name": "Volunteer Helper",
            "email": "volunteer@mtm.com",
            "phone": "+2301000007",
            "role": "volunteer",
            "is_verified": True,
        },
    ]

    try:
        for ud in users_data:
            existing = session.query(User).filter(User.email == ud["email"]).first()
            if not existing:
                new_user = User(
                    id=str(uuid.uuid4()),
                    full_name=ud["full_name"],
                    email=ud["email"],
                    phone=ud["phone"],
                    role_id=role_map.get(ud["role"]),
                    is_active=True,
                    is_verified=ud["is_verified"],
                    preferred_language="English",
                    consent_email=True,
                )
                session.add(new_user)
                session.flush()
                print(f"  ✅ Added: {ud['full_name']} ({ud['email']}) → {ud['role']}")
            else:
                print(f"  ℹ️  Already exists: {ud['email']}")
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error seeding users: {e}")
        raise


# =============================================================================
# 4) MEMBERSHIP PLANS
# =============================================================================
def seed_membership_plans(session):
    """Insert default membership plans."""
    print("\nSeeding membership plans...")
    from app.modules.members.models import MembershipPlan
    import json

    plans = [
        {
            "name": "Annual Membership",
            "description": "Standard annual membership with full access to events and community features.",
            "price": 1200.0,
            "duration_months": 12,
            "is_lifetime": False,
            "features": json.dumps(["All events access", "Digital membership card", "Forum participation", "Learning resources", "Community directory"]),
            "sort_order": 1,
        },
        {
            "name": "Lifetime Membership",
            "description": "One-time payment for lifetime access to all MTM platform features.",
            "price": 10000.0,
            "duration_months": None,
            "is_lifetime": True,
            "features": json.dumps(["Everything in Annual", "Lifetime access", "Priority event seating", "Exclusive badge", "Dedicated support"]),
            "sort_order": 2,
        },
    ]

    try:
        for plan_data in plans:
            existing = session.query(MembershipPlan).filter(MembershipPlan.name == plan_data["name"]).first()
            if not existing:
                plan = MembershipPlan(**plan_data)
                session.add(plan)
                print(f"  ✅ Created plan: {plan_data['name']}")
            else:
                print(f"  ⏭️  Plan already exists: {plan_data['name']}")
        session.commit()
    except Exception as e:
        print(f"  ❌ Error seeding plans: {e}")
        session.rollback()


# =============================================================================
# 5) SAMPLE EVENTS
# =============================================================================
def seed_sample_events(session):
    """Insert sample events for testing."""
    print("\nSeeding sample events...")
    from app.modules.events.models import Event
    from datetime import datetime

    organizer = session.query(User).join(Role).filter(Role.role_name == "event_manager").first()
    admin = session.query(User).join(Role).filter(Role.role_name == "admin").first()
    organizer_id = organizer.id if organizer else (admin.id if admin else None)

    if not organizer_id:
        print("  ⚠️  No event_manager/admin user found, skipping events.")
        return

    events_data = [
        {
            "title": "Ugadi Celebrations 2026",
            "description": "Grand Telugu New Year celebration with cultural programs, traditional food, and community gathering.",
            "event_type": "cultural",
            "status": "published",
            "start_date": datetime(2026, 3, 30, 10, 0),
            "end_date": datetime(2026, 3, 30, 18, 0),
            "location": "Port Louis Community Centre, Mauritius",
            "city": "Port Louis",
            "venue": "Port Louis Community Centre",
            "fee": 200.0,
            "is_free": False,
            "max_capacity": 500,
        },
        {
            "title": "Telugu Literature Meet",
            "description": "Meet Telugu authors and participate in literary discussions and book readings.",
            "event_type": "education",
            "status": "published",
            "start_date": datetime(2026, 4, 10, 14, 0),
            "end_date": datetime(2026, 4, 10, 18, 0),
            "location": "Curepipe Cultural Hall, Mauritius",
            "city": "Curepipe",
            "venue": "Curepipe Cultural Hall",
            "fee": 0.0,
            "is_free": True,
            "max_capacity": 200,
        },
        {
            "title": "Telugu Cultural Night",
            "description": "An evening of Telugu music, dance performances, and cultural showcase.",
            "event_type": "cultural",
            "status": "published",
            "start_date": datetime(2026, 4, 14, 18, 0),
            "end_date": datetime(2026, 4, 14, 22, 0),
            "location": "Rose Hill Town Hall, Mauritius",
            "city": "Rose Hill",
            "venue": "Rose Hill Town Hall",
            "fee": 350.0,
            "is_free": False,
            "max_capacity": 300,
        },
        {
            "title": "Annual Mahasabha Conference 2026",
            "description": "The flagship annual conference bringing together Telugu community leaders.",
            "event_type": "conference",
            "status": "published",
            "start_date": datetime(2026, 6, 15, 9, 0),
            "end_date": datetime(2026, 6, 16, 17, 0),
            "location": "Ebene Cybercity Conference Centre, Mauritius",
            "city": "Ebene",
            "venue": "Ebene Cybercity Conference Centre",
            "fee": 500.0,
            "is_free": False,
            "max_capacity": 1000,
        },
    ]

    try:
        existing = session.query(Event).count()
        if existing > 0:
            print(f"  ⏭️  {existing} events already exist, skipping.")
            return

        for event_data in events_data:
            event = Event(organizer_id=organizer_id, **event_data)
            session.add(event)
            print(f"  ✅ Created event: {event_data['title']}")
        session.commit()
    except Exception as e:
        print(f"  ❌ Error seeding events: {e}")
        session.rollback()


# =============================================================================
# MAIN
# =============================================================================
def main():
    """Run all seeding operations."""
    print("=" * 60)
    print("  MTM Platform — Database Seeding (PRD-Aligned)")
    print("=" * 60)

    session = SessionLocal()

    try:
        seed_roles(session)
        seed_permissions(session)
        seed_users(session)
        seed_membership_plans(session)
        seed_sample_events(session)

        print("\n" + "=" * 60)
        print("  ✅ Database seeding completed successfully!")
        print("=" * 60)
        print("\n  Sample Credentials:")
        print("  ─────────────────────────────────────────────")
        print("  Admin:            admin@mtm.com / admin123")
        print("  Finance Admin:    finance@mtm.com / finance123")
        print("  Event Manager:    events@mtm.com / events123")
        print("  Committee Member: committee@mtm.com / committee123")
        print("  Moderator:        moderator@mtm.com / moderator123")
        print("  Member:           member@mtm.com / member123")
        print("  Volunteer:        volunteer@mtm.com / volunteer123")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n  ❌ Seeding failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
