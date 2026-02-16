"""
Seed script to populate database with roles, permissions, and sample users.
Uses existing database connection from app.core.database
"""

import uuid
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.auth.models import Role, User, Permission


def seed_roles(session):
    """Insert default roles into the database."""
    print("Seeding roles...")
    
    roles_data = [
        {"role_name": "admin", "description": "Administrator with full system access"},
        {"role_name": "moderator", "description": "Moderator can manage content and monitor users"},
        {"role_name": "organizer", "description": "Organizer can create and manage events"},
        {"role_name": "member", "description": "Regular platform member with standard access"},
        {"role_name": "user", "description": "Basic user account"},
    ]
    
    try:
        for role_data in roles_data:
            # Check if role already exists
            existing_role = session.query(Role).filter(Role.role_name == role_data["role_name"]).first()
            
            if not existing_role:
                # Create new role if it doesn't exist
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
        print(f"  Error seeding roles: {e}")
        raise


def seed_permissions(session):
    """Insert permissions for roles."""
    print("\nSeeding permissions...")
    
    # Get roles
    admin_role = session.query(Role).filter(Role.role_name == "admin").first()
    moderator_role = session.query(Role).filter(Role.role_name == "moderator").first()
    organizer_role = session.query(Role).filter(Role.role_name == "organizer").first()
    user_role = session.query(Role).filter(Role.role_name == "user").first()
    
    permissions_data = [
        # Admin permissions (all resources)
        {"role_id": admin_role.role_id if admin_role else None, "permission_name": "admin.read", "resource": "admin", "action": "read"},
        {"role_id": admin_role.role_id if admin_role else None, "permission_name": "admin.write", "resource": "admin", "action": "write"},
        
        # User management
        {"role_id": admin_role.role_id if admin_role else None, "permission_name": "users.create", "resource": "users", "action": "create"},
        {"role_id": admin_role.role_id if admin_role else None, "permission_name": "users.read", "resource": "users", "action": "read"},
        {"role_id": admin_role.role_id if admin_role else None, "permission_name": "users.update", "resource": "users", "action": "update"},
        {"role_id": admin_role.role_id if admin_role else None, "permission_name": "users.delete", "resource": "users", "action": "delete"},
        
        # Moderator permissions
        {"role_id": moderator_role.role_id if moderator_role else None, "permission_name": "users.read", "resource": "users", "action": "read"},
        {"role_id": moderator_role.role_id if moderator_role else None, "permission_name": "content.moderate", "resource": "content", "action": "moderate"},
        
        # Event organizer permissions
        {"role_id": organizer_role.role_id if organizer_role else None, "permission_name": "events.create", "resource": "events", "action": "create"},
        {"role_id": organizer_role.role_id if organizer_role else None, "permission_name": "events.read", "resource": "events", "action": "read"},
        {"role_id": organizer_role.role_id if organizer_role else None, "permission_name": "events.update", "resource": "events", "action": "update"},
        
        # User permissions
        {"role_id": user_role.role_id if user_role else None, "permission_name": "profile.read", "resource": "profile", "action": "read"},
        {"role_id": user_role.role_id if user_role else None, "permission_name": "profile.update", "resource": "profile", "action": "update"},
    ]
    
    try:
        for perm_data in permissions_data:
            if perm_data["role_id"]:
                existing_perm = session.query(Permission).filter(
                    Permission.permission_name == perm_data["permission_name"]
                ).first()
                
                if not existing_perm:
                    new_perm = Permission(
                        permission_id=str(uuid.uuid4()),
                        permission_name=perm_data["permission_name"],
                        resource=perm_data["resource"],
                        action=perm_data["action"],
                        role_id=perm_data["role_id"]
                    )
                    session.add(new_perm)
                    session.flush()
                    print(f"  ✅ Added permission: {perm_data['permission_name']}")
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  Error seeding permissions: {e}")
        raise


def seed_users(session):
    """Insert sample users into the database with hashed passwords."""
    print("\nSeeding users...")
    
    # Get role IDs
    admin_role = session.query(Role).filter(Role.role_name == "admin").first()
    moderator_role = session.query(Role).filter(Role.role_name == "moderator").first()
    organizer_role = session.query(Role).filter(Role.role_name == "organizer").first()
    member_role = session.query(Role).filter(Role.role_name == "member").first()
    user_role = session.query(Role).filter(Role.role_name == "user").first()
    
    users_data = [
        {
            "full_name": "Admin User",
            "email": "admin@mtm.com",
            "phone": "+1234567890",
            "password": "admin123",
            "role_id": admin_role.role_id if admin_role else None,
            "is_verified": True
        },
        {
            "full_name": "Moderator User",
            "email": "moderator@mtm.com",
            "phone": "+1234567891",
            "password": "moderator123",
            "role_id": moderator_role.role_id if moderator_role else None,
            "is_verified": True
        },
        {
            "full_name": "Event Organizer",
            "email": "organizer@mtm.com",
            "phone": "+1234567892",
            "password": "organizer123",
            "role_id": organizer_role.role_id if organizer_role else None,
            "is_verified": True
        },
        {
            "full_name": "John Member",
            "email": "member@mtm.com",
            "phone": "+1234567893",
            "password": "member123",
            "role_id": member_role.role_id if member_role else None,
            "is_verified": True
        },
        {
            "full_name": "Jane User",
            "email": "user@mtm.com",
            "phone": "+1234567894",
            "password": "user123",
            "role_id": user_role.role_id if user_role else None,
            "is_verified": False
        },
    ]
    
    try:
        for user_data in users_data:
            # Check if user already exists
            existing_user = session.query(User).filter(User.email == user_data["email"]).first()
            
            if not existing_user:
                # Create new user if it doesn't exist
                new_user = User(
                    id=str(uuid.uuid4()),
                    full_name=user_data["full_name"],
                    email=user_data["email"],
                    phone=user_data["phone"],
                    password_hash=hash_password(user_data["password"]),
                    role_id=user_data["role_id"],
                    is_active=True,
                    is_verified=user_data["is_verified"]
                )
                session.add(new_user)
                session.flush()
                print(f"  ✅ Added user: {user_data['full_name']} ({user_data['email']})")
            else:
                print(f"  ℹ️  User already exists: {user_data['email']}")
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  Error seeding users: {e}")
        raise


def main():
    """Run all seeding operations."""
    print("="*60)
    print("Database Seeding Started")
    print("="*60)
    
    session = SessionLocal()
    
    try:
        seed_roles(session)
        seed_permissions(session)
        seed_users(session)
        
        print("\n" + "="*60)
        print("✅ Database seeding completed successfully!")
        print("="*60)
        print("\nSample Credentials for Testing:")
        print("  Admin:      admin@mtm.com / admin123")
        print("  Moderator:  moderator@mtm.com / moderator123")
        print("  Organizer:  organizer@mtm.com / organizer123")
        print("  Member:     member@mtm.com / member123")
        print("  User:       user@mtm.com / user123")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\nSeeding failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
