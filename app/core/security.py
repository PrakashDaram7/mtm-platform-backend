"""Security utilities and JWT token handling with RBAC support."""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.auth.models import User, Role

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-12345678")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme
security = HTTPBearer()


class TokenData:
    """Token payload data."""
    def __init__(self, user_id: str, email: str, roles: List[str]):
        self.user_id = user_id
        self.email = email
        self.roles = roles


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str, roles: List[str], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        user_id: User ID
        email: User email
        roles: List of user roles
        expires_delta: Token expiration time
        
    Returns:
        JWT access token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "user_id": user_id,
        "email": email,
        "roles": roles,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: str, email: str) -> str:
    """Create a JWT refresh token.
    
    Args:
        user_id: User ID
        email: User email
        
    Returns:
        JWT refresh token
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "user_id": user_id,
        "email": email,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> TokenData:
    """Verify and decode a JWT access token.
    
    Args:
        token: JWT token
        
    Returns:
        TokenData object
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        roles: List[str] = payload.get("roles", [])
        
        if user_id is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return TokenData(user_id=user_id, email=email, roles=roles)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        TokenData object
    """
    token = credentials.credentials
    return verify_access_token(token)


async def get_db() -> any:
    """Get database session dependency.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_from_db(user_id: str, db: Session) -> Optional[User]:
    """Get user from database by ID.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        User object or None
    """
    return db.query(User).filter(User.id == user_id).first()


def user_has_role(user: User, required_role: str) -> bool:
    """Check if user has a specific role.
    
    Args:
        user: User object
        required_role: Role name to check
        
    Returns:
        True if user has role, False otherwise
    """
    if not user or not user.role:
        return False
    return user.role.role_name == required_role


def user_has_any_role(user: User, required_roles: List[str]) -> bool:
    """Check if user has any of the specified roles.
    
    Args:
        user: User object
        required_roles: List of role names
        
    Returns:
        True if user has any of the roles
    """
    if not user or not user.role:
        return False
    return user.role.role_name in required_roles


class RBACService:
    """Service for Role-Based Access Control operations."""
    
    @staticmethod
    def check_permission(user: User, resource: str, action: str) -> bool:
        """Check if user has permission for a resource action.
        
        Args:
            user: User object
            resource: Resource name (e.g., 'users', 'events', 'payments')
            action: Action name (e.g., 'create', 'read', 'update', 'delete')
            
        Returns:
            True if user has permission, False otherwise
        """
        if not user or not user.role:
            return False
        
        # Check permissions for user's role
        for permission in user.role.permissions:
            if permission.resource == resource and permission.action == action:
                return True
        
        return False
    
    @staticmethod
    def get_user_permissions(user: User) -> List[Dict[str, str]]:
        """Get all permissions for a user's role.
        
        Args:
            user: User object
            
        Returns:
            List of permission dictionaries
        """
        if not user or not user.role:
            return []
        
        return [
            {
                "resource": perm.resource,
                "action": perm.action,
                "permission_name": perm.permission_name
            }
            for perm in user.role.permissions
        ]
