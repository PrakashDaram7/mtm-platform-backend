"""Admin module services for user management."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.modules.auth.models import User, Role
from app.core.security import hash_password


class AdminUserService:
    """Service for admin user management operations."""

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 10) -> Dict:
        """Get all users with pagination (admin only).
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            Dictionary with users list and pagination info
        """
        try:
            users = db.query(User).offset(skip).limit(limit).all()
            total = db.query(User).count()
            
            return {
                "success": True,
                "message": "Users retrieved successfully",
                "total": total,
                "skip": skip,
                "limit": limit,
                "users": [
                    {
                        "id": user.id,
                        "full_name": user.full_name,
                        "email": user.email,
                        "phone": user.phone,
                        "is_active": user.is_active,
                        "is_verified": user.is_verified,
                        "role_name": user.role.role_name if user.role else None,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "last_login": user.last_login.isoformat() if user.last_login else None
                    }
                    for user in users
                ]
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving users: {str(e)}",
                "total": 0,
                "users": []
            }

    @staticmethod
    def get_user_detail(db: Session, user_id: str) -> Dict:
        """Get detailed user information (admin only).
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary with detailed user information
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "user": None
                }
            
            return {
                "success": True,
                "message": "User details retrieved successfully",
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "role_id": user.role_id,
                    "role_name": user.role.role_name if user.role else None,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving user: {str(e)}",
                "user": None
            }

    @staticmethod
    def create_user(db: Session, full_name: str, email: str, phone: str = None, 
                   password: str = None, role_name: str = "user") -> Dict:
        """Create a new user (admin only).
        
        Args:
            db: Database session
            full_name: User full name
            email: User email
            phone: User phone number
            password: User password
            role_name: Role to assign to user
            
        Returns:
            Dictionary with created user data
        """
        try:
            # Check if email already exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                return {
                    "success": False,
                    "message": "User with this email already exists",
                    "user": None
                }
            
            # Get role
            role = db.query(Role).filter(Role.role_name == role_name).first()
            if not role:
                return {
                    "success": False,
                    "message": f"Role '{role_name}' not found",
                    "user": None
                }
            
            # Validate and hash password if provided
            password_hash = None
            if password:
                try:
                    password_hash = hash_password(password)
                except ValueError as e:
                    return {
                        "success": False,
                        "message": str(e),
                        "user": None
                    }
            
            # Create user
            new_user = User(
                full_name=full_name,
                email=email,
                phone=phone,
                password_hash=password_hash,
                role_id=role.role_id,
                is_active=True,
                is_verified=False
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            return {
                "success": True,
                "message": "User created successfully",
                "user": {
                    "id": new_user.id,
                    "full_name": new_user.full_name,
                    "email": new_user.email,
                    "phone": new_user.phone,
                    "role_name": role.role_name,
                    "is_active": new_user.is_active,
                    "created_at": new_user.created_at.isoformat()
                }
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error creating user: {str(e)}",
                "user": None
            }

    @staticmethod
    def update_user(db: Session, user_id: str, **kwargs) -> Dict:
        """Update user information (admin only).
        
        Args:
            db: Database session
            user_id: User ID to update
            **kwargs: Fields to update (full_name, phone, is_active, is_verified, role_name)
            
        Returns:
            Dictionary with updated user data
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "user": None
                }
            
            # Update fields
            if "full_name" in kwargs and kwargs["full_name"]:
                user.full_name = kwargs["full_name"]
            if "phone" in kwargs:
                user.phone = kwargs["phone"]
            if "is_active" in kwargs:
                user.is_active = kwargs["is_active"]
            if "is_verified" in kwargs:
                user.is_verified = kwargs["is_verified"]
            
            # Handle role update
            if "role_name" in kwargs and kwargs["role_name"]:
                role = db.query(Role).filter(Role.role_name == kwargs["role_name"]).first()
                if not role:
                    return {
                        "success": False,
                        "message": f"Role '{kwargs['role_name']}' not found",
                        "user": None
                    }
                user.role_id = role.role_id
            
            db.commit()
            db.refresh(user)
            
            return {
                "success": True,
                "message": "User updated successfully",
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "role_name": user.role.role_name if user.role else None,
                    "updated_at": user.updated_at.isoformat()
                }
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error updating user: {str(e)}",
                "user": None
            }

    @staticmethod
    def delete_user(db: Session, user_id: str) -> Dict:
        """Delete a user (admin only).
        
        Args:
            db: Database session
            user_id: User ID to delete
            
        Returns:
            Dictionary with success/failure message
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            db.delete(user)
            db.commit()
            
            return {
                "success": True,
                "message": "User deleted successfully"
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error deleting user: {str(e)}"
            }

    @staticmethod
    def disable_user(db: Session, user_id: str) -> Dict:
        """Disable a user account (admin only).
        
        Args:
            db: Database session
            user_id: User ID to disable
            
        Returns:
            Dictionary with updated user data
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "user": None
                }
            
            user.is_active = False
            db.commit()
            db.refresh(user)
            
            return {
                "success": True,
                "message": "User disabled successfully",
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_active": user.is_active
                }
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error disabling user: {str(e)}",
                "user": None
            }

    @staticmethod
    def enable_user(db: Session, user_id: str) -> Dict:
        """Enable a disabled user account (admin only).
        
        Args:
            db: Database session
            user_id: User ID to enable
            
        Returns:
            Dictionary with updated user data
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "user": None
                }
            
            user.is_active = True
            db.commit()
            db.refresh(user)
            
            return {
                "success": True,
                "message": "User enabled successfully",
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_active": user.is_active
                }
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error enabling user: {str(e)}",
                "user": None
            }

    @staticmethod
    def change_user_role(db: Session, user_id: str, role_name: str) -> Dict:
        """Change user role (admin only).
        
        Args:
            db: Database session
            user_id: User ID
            role_name: New role name
            
        Returns:
            Dictionary with updated user data
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "user": None
                }
            
            role = db.query(Role).filter(Role.role_name == role_name).first()
            
            if not role:
                return {
                    "success": False,
                    "message": f"Role '{role_name}' not found",
                    "user": None
                }
            
            old_role = user.role.role_name if user.role else None
            user.role_id = role.role_id
            db.commit()
            db.refresh(user)
            
            return {
                "success": True,
                "message": "User role changed successfully",
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "old_role": old_role,
                    "new_role": role.role_name
                }
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error changing user role: {str(e)}",
                "user": None
            }

    @staticmethod
    def search_users(db: Session, query: str, field: str = "email") -> Dict:
        """Search users by field (admin only).
        
        Args:
            db: Database session
            query: Search query
            field: Field to search in (email, full_name, phone)
            
        Returns:
            Dictionary with matching users
        """
        try:
            if field == "email":
                users = db.query(User).filter(User.email.contains(query)).all()
            elif field == "full_name":
                users = db.query(User).filter(User.full_name.contains(query)).all()
            elif field == "phone":
                users = db.query(User).filter(User.phone.contains(query)).all()
            else:
                return {
                    "success": False,
                    "message": f"Invalid search field: {field}",
                    "users": []
                }
            
            return {
                "success": True,
                "message": f"Found {len(users)} user(s)",
                "users": [
                    {
                        "id": user.id,
                        "full_name": user.full_name,
                        "email": user.email,
                        "phone": user.phone,
                        "role_name": user.role.role_name if user.role else None
                    }
                    for user in users
                ]
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error searching users: {str(e)}",
                "users": []
            }

    @staticmethod
    def get_analytics(db: Session) -> Dict:
        """Get dashboard analytics data (admin only).
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with analytics data
        """
        try:
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active == True).count()
            verified_users = db.query(User).filter(User.is_verified == True).count()
            admin_users = db.query(User).join(Role).filter(Role.role_name == "admin").count()
            member_users = db.query(User).join(Role).filter(Role.role_name == "member").count()
            
            # Get role distribution
            role_distribution = db.query(Role.role_name, func.count(User.id)).join(User, User.role_id == Role.role_id, isouter=True).group_by(Role.role_name).all()
            
            return {
                "success": True,
                "message": "Analytics retrieved successfully",
                "analytics": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "verified_users": verified_users,
                    "inactive_users": total_users - active_users,
                    "admin_users": admin_users,
                    "member_users": member_users,
                    "role_distribution": [
                        {
                            "role_name": role_name,
                            "count": count
                        }
                        for role_name, count in role_distribution if role_name is not None
                    ]
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving analytics: {str(e)}",
                "analytics": None
            }

    @staticmethod
    def get_all_roles(db: Session) -> Dict:
        """Get all roles.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with roles list
        """
        try:
            roles = db.query(Role).all()
            
            return {
                "success": True,
                "message": "Roles retrieved successfully",
                "roles": [
                    {
                        "id": role.role_id,
                        "name": role.role_name,
                        "description": role.description if hasattr(role, 'description') else None,
                        "created_at": role.created_at.isoformat() if hasattr(role, 'created_at') and role.created_at else None
                    }
                    for role in roles
                ]
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving roles: {str(e)}",
                "roles": []
            }

    @staticmethod
    def create_role(db: Session, role_name: str, description: str = None) -> Dict:
        """Create a new role.
        
        Args:
            db: Database session
            role_name: Name of the role
            description: Role description (optional)
            
        Returns:
            Created role data
        """
        try:
            # Check if role already exists
            existing_role = db.query(Role).filter(Role.role_name == role_name).first()
            if existing_role:
                return {
                    "success": False,
                    "message": f"Role '{role_name}' already exists",
                    "role": None
                }
            
            new_role = Role(
                role_name=role_name,
                description=description if description else f"Role for {role_name}"
            )
            
            db.add(new_role)
            db.commit()
            db.refresh(new_role)
            
            return {
                "success": True,
                "message": f"Role '{role_name}' created successfully",
                "role": {
                    "id": new_role.role_id,
                    "name": new_role.role_name,
                    "description": new_role.description if hasattr(new_role, 'description') else None
                }
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error creating role: {str(e)}",
                "role": None
            }

    @staticmethod
    def update_role(db: Session, role_id: str, role_name: str = None, description: str = None) -> Dict:
        """Update a role.
        
        Args:
            db: Database session
            role_id: Role ID
            role_name: New role name (optional)
            description: New description (optional)
            
        Returns:
            Updated role data
        """
        try:
            role = db.query(Role).filter(Role.role_id == role_id).first()
            
            if not role:
                return {
                    "success": False,
                    "message": f"Role not found",
                    "role": None
                }
            
            # Check if new role name already exists
            if role_name and role_name != role.role_name:
                existing = db.query(Role).filter(Role.role_name == role_name).first()
                if existing:
                    return {
                        "success": False,
                        "message": f"Role '{role_name}' already exists",
                        "role": None
                    }
                role.role_name = role_name
            
            if description:
                if hasattr(role, 'description'):
                    role.description = description
            
            db.commit()
            db.refresh(role)
            
            return {
                "success": True,
                "message": "Role updated successfully",
                "role": {
                    "id": role.role_id,
                    "name": role.role_name,
                    "description": role.description if hasattr(role, 'description') else None
                }
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error updating role: {str(e)}",
                "role": None
            }

    @staticmethod
    def delete_role(db: Session, role_id: str) -> Dict:
        """Delete a role.
        
        Args:
            db: Database session
            role_id: Role ID to delete
            
        Returns:
            Success/failure message
        """
        try:
            role = db.query(Role).filter(Role.role_id == role_id).first()
            
            if not role:
                return {
                    "success": False,
                    "message": "Role not found"
                }
            
            # Check if any users have this role
            users_with_role = db.query(User).filter(User.role_id == role_id).count()
            if users_with_role > 0:
                return {
                    "success": False,
                    "message": f"Cannot delete role '{role.role_name}'. {users_with_role} user(s) assigned to this role."
                }
            
            db.delete(role)
            db.commit()
            
            return {
                "success": True,
                "message": f"Role deleted successfully"
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error deleting role: {str(e)}"
            }
