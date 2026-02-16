

import json
import secrets
import string
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from enum import Enum

try:
    import redis
except ImportError:
    raise ImportError('redis package is required. Install it with: pip install redis')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.modules.auth.models import OTP, User

class OTPConfig:
    """Configuration for OTP generation and validation."""

    DEFAULT_LENGTH = 6  # 6-digit OTP
    DEFAULT_EXPIRY_MINUTES = 2  # OTP expires in 10 minutes
    DEFAULT_EXPIRY_SECONDS = DEFAULT_EXPIRY_MINUTES * 60
    MAX_ATTEMPTS = 3  # Maximum failed validation attempts
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    OTP_KEY_PREFIX = "otp:"  # Redis key prefix for OTPs


class OTPType(str, Enum):
    """Types of OTP."""

    EMAIL = "email"
    SMS = "sms"
   


# Redis client initialization - Lazy loading to avoid startup failure
_redis_client = None
_redis_connection_error = None


def _get_redis_client():
    """Get Redis client with lazy initialization and error handling."""
    global _redis_client, _redis_connection_error
    
    if _redis_client is not None:
        return _redis_client
    
    if _redis_connection_error is not None:
        # Redis connection has already been attempted and failed - don't retry
        raise RuntimeError(_redis_connection_error)
    
    try:
        _redis_client = redis.Redis(
            host=OTPConfig.REDIS_HOST,
            port=OTPConfig.REDIS_PORT,
            db=OTPConfig.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        # Test connection
        _redis_client.ping()
        print(f"✓ Redis connection established at {OTPConfig.REDIS_HOST}:{OTPConfig.REDIS_PORT}")
        return _redis_client
    except Exception as e:
        error_msg = (
            f"Failed to connect to Redis at {OTPConfig.REDIS_HOST}:{OTPConfig.REDIS_PORT}. "
            f"Error: {str(e)}\n"
            f"Solutions:\n"
            f"  1. Start Redis server (Windows/WSL/Docker)\n"
            f"  2. Check Redis is running on the configured host:port\n"
            f"  3. Update REDIS_HOST and REDIS_PORT in OTPConfig or environment variables"
        )
        _redis_connection_error = error_msg
        print(f"⚠ WARNING: {error_msg}")
        raise RuntimeError(error_msg)


class OTPService:
    """Service for generating and managing OTPs using Redis storage."""

    @staticmethod
    def _get_redis_key(identifier: str) -> str:
        """Generate Redis key for OTP storage.

        Args:
            identifier: Unique identifier

        Returns:
            Redis key
        """
        return f"{OTPConfig.OTP_KEY_PREFIX}{identifier}"

    @staticmethod
    def generate_numeric_otp(
        length: int = OTPConfig.DEFAULT_LENGTH,
    ) -> str:
        """Generate a numeric OTP.

        Args:
            length: Length of the OTP (default: 6 digits)

        Returns:
            A numeric OTP string
        """
        if length < 4:
            raise ValueError("OTP length must be at least 4 digits")

        digits = string.digits
        otp = "".join(secrets.choice(digits) for _ in range(length))
        return otp

    @staticmethod
    def generate_alphanumeric_otp(
        length: int = 8,
    ) -> str:
        """Generate an alphanumeric OTP.

        Args:
            length: Length of the OTP (default: 8 characters)

        Returns:
            An alphanumeric OTP string
        """
        if length < 6:
            raise ValueError("OTP length must be at least 6 characters")

        chars = string.ascii_uppercase + string.digits
        otp = "".join(secrets.choice(chars) for _ in range(length))
        return otp

    @staticmethod
    def _hash_otp(otp: str) -> str:
        """Hash an OTP for secure storage.

        Args:
            otp: The OTP to hash

        Returns:
            Hashed OTP string
        """
        return hashlib.sha256(otp.encode()).hexdigest()

    @staticmethod
    def store_otp(
        identifier: str,
        otp: str,
        otp_type: OTPType = OTPType.EMAIL,
        expiry_minutes: int = OTPConfig.DEFAULT_EXPIRY_MINUTES,
        user_id: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Dict:
        """Store an OTP with metadata in Redis and Database.

        Args:
            identifier: Unique identifier (email, phone, user_id, etc.)
            otp: The OTP value
            otp_type: Type of OTP (email, sms, totp)
            expiry_minutes: Minutes until OTP expires
            user_id: Optional user ID for database relationship
            phone: Phone number for OTP (required for SMS OTP)

        Returns:
            Dictionary containing OTP metadata
        """
        now = datetime.utcnow()
        expiry_time = now + timedelta(minutes=expiry_minutes)
        expiry_seconds = expiry_minutes * 60

        otp_data = {
            "otp": OTPService._hash_otp(otp),
            "otp_type": otp_type.value,
            "created_at": now.isoformat(),
            "expires_at": expiry_time.isoformat(),
            "attempts": 0,
            "verified": False,
        }

        redis_key = OTPService._get_redis_key(identifier)

        # Store in Redis with automatic expiry (TTL)
        _get_redis_client().setex(
            name=redis_key,
            time=expiry_seconds,
            value=json.dumps(otp_data),
        )

        # Store in Database
        db = SessionLocal()
        try:
            otp_record = OTP(
                user_id=user_id,
                phone=phone or identifier,
                otp_code=otp,
                expires_at=expiry_time,
                is_used=False,
            )
            db.add(otp_record)
            db.commit()
            db.refresh(otp_record)
        except Exception as e:
            db.rollback()
            print(f"Warning: Failed to store OTP in database: {e}")
        finally:
            db.close()

        return {
            "identifier": identifier,
            "expires_at": expiry_time.isoformat(),
            "otp_type": otp_type.value,
            "ttl_seconds": expiry_seconds,
        }

    @staticmethod
    def validate_otp(
        identifier: str,
        otp: str,
    ) -> Tuple[bool, str]:
        """Validate an OTP from Redis and fallback to Database.

        Args:
            identifier: Unique identifier
            otp: The OTP to validate

        Returns:
            Tuple of (is_valid, message)
        """
        redis_key = OTPService._get_redis_key(identifier)
        otp_value = _get_redis_client().get(redis_key)

        if not otp_value:
            # Fallback to database if not in Redis
            return OTPService._validate_otp_from_db(identifier, otp)

        otp_data = json.loads(otp_value)

        # Check if OTP is already verified
        if otp_data.get("verified"):
            return False, "OTP has already been used."

        # Check attempt limit
        attempts = otp_data.get("attempts", 0)
        if attempts >= OTPConfig.MAX_ATTEMPTS:
            _get_redis_client().delete(redis_key)
            return False, "Too many failed attempts. Please request a new OTP."

        # Validate OTP
        hashed_input = OTPService._hash_otp(otp)
        if hashed_input != otp_data["otp"]:
            otp_data["attempts"] = attempts + 1
            remaining = OTPConfig.MAX_ATTEMPTS - otp_data["attempts"]

            # Update attempts in Redis while preserving TTL
            ttl = _get_redis_client().ttl(redis_key)
            if ttl > 0:
                _get_redis_client().setex(
                    name=redis_key,
                    time=ttl,
                    value=json.dumps(otp_data),
                )

            return False, f"Invalid OTP. {remaining} attempts remaining."

        # Mark as verified in Redis
        otp_data["verified"] = True
        otp_data["verified_at"] = datetime.utcnow().isoformat()

        # Update in Redis
        ttl = _get_redis_client().ttl(redis_key)
        if ttl > 0:
            _get_redis_client().setex(
                name=redis_key,
                time=ttl,
                value=json.dumps(otp_data),
            )

        # Mark as used in Database
        OTPService._mark_otp_as_used_in_db(identifier, otp)

        return True, "OTP validated successfully."

    @staticmethod
    def _validate_otp_from_db(identifier: str, otp: str) -> Tuple[bool, str]:
        """Fallback validation from database when Redis is unavailable.

        Args:
            identifier: Unique identifier (phone number)
            otp: The OTP to validate

        Returns:
            Tuple of (is_valid, message)
        """
        db = SessionLocal()
        try:
            # Find the most recent, unused OTP for this phone/identifier
            otp_record = db.query(OTP).filter(
                OTP.phone == identifier,
                OTP.is_used == False,
                OTP.expires_at > datetime.utcnow()
            ).order_by(OTP.created_at.desc()).first()

            if not otp_record:
                return False, "OTP not found or expired. Please request a new OTP."

            # Validate OTP
            if otp_record.otp_code != otp:
                return False, "Invalid OTP."

            # Mark as used
            otp_record.is_used = True
            db.commit()

            return True, "OTP validated successfully."
        except Exception as e:
            db.rollback()
            return False, f"Error validating OTP: {str(e)}"
        finally:
            db.close()

    @staticmethod
    def _mark_otp_as_used_in_db(identifier: str, otp: str) -> bool:
        """Mark OTP as used in database.

        Args:
            identifier: Unique identifier
            otp: The OTP code

        Returns:
            True if updated, False otherwise
        """
        db = SessionLocal()
        try:
            # Find the OTP record
            otp_record = db.query(OTP).filter(
                OTP.phone == identifier,
                OTP.otp_code == otp,
                OTP.is_used == False
            ).first()

            if otp_record:
                otp_record.is_used = True
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Warning: Failed to update OTP in database: {e}")
            return False
        finally:
            db.close()

    @staticmethod
    def get_otp_from_db(identifier: str) -> Optional[Dict]:
        """Get OTP details from database.

        Args:
            identifier: Unique identifier (phone number)

        Returns:
            OTP record details or None
        """
        db = SessionLocal()
        try:
            otp_record = db.query(OTP).filter(
                OTP.phone == identifier,
                OTP.expires_at > datetime.utcnow()
            ).order_by(OTP.created_at.desc()).first()

            if otp_record:
                return {
                    "otp_id": otp_record.otp_id,
                    "phone": otp_record.phone,
                    "is_used": otp_record.is_used,
                    "created_at": otp_record.created_at.isoformat(),
                    "expires_at": otp_record.expires_at.isoformat(),
                }
            return None
        except Exception as e:
            print(f"Warning: Failed to fetch OTP from database: {e}")
            return None
        finally:
            db.close()

        """Check if an OTP is verified.

        Args:
            identifier: Unique identifier

        Returns:
            True if OTP is verified, False otherwise
        """
        redis_key = OTPService._get_redis_key(identifier)
        otp_value = _get_redis_client().get(redis_key)

        if not otp_value:
            return False

        otp_data = json.loads(otp_value)
        return otp_data.get("verified", False)

    @staticmethod
    def clear_otp(identifier: str) -> bool:
        """Clear an OTP from Redis.

        Args:
            identifier: Unique identifier

        Returns:
            True if OTP was cleared, False if not found
        """
        redis_key = OTPService._get_redis_key(identifier)
        result = _get_redis_client().delete(redis_key)
        return result > 0

    @staticmethod
    def get_otp_info(identifier: str) -> Optional[Dict]:
        """Get OTP information (without revealing the actual OTP).

        Args:
            identifier: Unique identifier

        Returns:
            OTP metadata or None if not found
        """
        redis_key = OTPService._get_redis_key(identifier)
        otp_value = _get_redis_client().get(redis_key)

        if not otp_value:
            return None

        otp_data = json.loads(otp_value)
        ttl = _get_redis_client().ttl(redis_key)

        return {
            "otp_type": otp_data.get("otp_type"),
            "created_at": otp_data.get("created_at"),
            "expires_at": otp_data.get("expires_at"),
            "verified": otp_data.get("verified"),
            "attempts": otp_data.get("attempts"),
            "ttl_seconds": ttl,
        }

    @staticmethod
    def get_remaining_ttl(identifier: str) -> Optional[int]:
        """Get remaining TTL for an OTP in seconds.

        Args:
            identifier: Unique identifier

        Returns:
            Remaining TTL in seconds, or None if OTP not found
        """
        redis_key = OTPService._get_redis_key(identifier)
        ttl = _get_redis_client().ttl(redis_key)
        return ttl if ttl > 0 else None

    @staticmethod
    def get_redis_stats() -> Dict:
        """Get Redis stats for OTP storage.

        Returns:
            Dictionary containing Redis statistics
        """
        pattern = f"{OTPConfig.OTP_KEY_PREFIX}*"
        otp_keys = _get_redis_client().keys(pattern)

        verified_count = 0
        for key in otp_keys:
            otp_value = _get_redis_client().get(key)
            if otp_value:
                otp_data = json.loads(otp_value)
                if otp_data.get("verified"):
                    verified_count += 1

        return {
            "total_otps": len(otp_keys),
            "verified_otps": verified_count,
            "pending_otps": len(otp_keys) - verified_count,
        }


class UserAuthService:
    """Service for user authentication operations."""

    @staticmethod
    def format_user_response(user) -> Dict:
        """Format user object for API response.
        
        Args:
            user: User model instance
            
        Returns:
            Dictionary with user information including role
        """
        user_data = {
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
        
        # Include role if exists
        if user.role:
            user_data["role"] = {
                "role_id": user.role.role_id,
                "role_name": user.role.role_name,
                "description": user.role.description
            }
        else:
            user_data["role"] = None
        
        return user_data

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid email format
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            True if valid phone format
        """
        import re
        # Accepts international format with +, digits, hyphens, spaces
        pattern = r'^\+?1?\d{9,15}$'
        clean_phone = phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        return re.match(pattern, clean_phone) is not None

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number by removing extra characters.
        
        Args:
            phone: Raw phone number
            
        Returns:
            Normalized phone number
        """
        return phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")


class UserService:
    """Service for user CRUD operations."""

    @staticmethod
    def create_user(db, email: str, full_name: str, phone: str = None) -> Dict:
        """Create a new user.
        
        Args:
            db: Database session
            email: User email
            full_name: User full name
            phone: Optional phone number
            
        Returns:
            Dictionary with user data or error
        """
        from app.modules.auth.models import User
        
        try:
            # Check if user exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                return {
                    "success": False,
                    "message": "User with this email already exists",
                    "user": None
                }
            
            # Create new user
            user = User(
                email=email,
                full_name=full_name,
                phone=phone,
                is_active=True,
                is_verified=False
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return {
                "success": True,
                "message": "User created successfully",
                "user": UserAuthService.format_user_response(user)
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error creating user: {str(e)}",
                "user": None
            }

    @staticmethod
    def get_user_by_id(db, user_id: str) -> Dict:
        """Get user by ID.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary with user data or None
        """
        from app.modules.auth.models import User
        
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
                "message": "User retrieved successfully",
                "user": UserAuthService.format_user_response(user)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving user: {str(e)}",
                "user": None
            }

    @staticmethod
    def get_user_by_email(db, email: str) -> Dict:
        """Get user by email.
        
        Args:
            db: Database session
            email: User email
            
        Returns:
            Dictionary with user data or None
        """
        from app.modules.auth.models import User
        
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "user": None
                }
            
            return {
                "success": True,
                "message": "User retrieved successfully",
                "user": UserAuthService.format_user_response(user)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving user: {str(e)}",
                "user": None
            }

    @staticmethod
    def get_user_by_phone(db, phone: str) -> Dict:
        """Get user by phone.
        
        Args:
            db: Database session
            phone: User phone
            
        Returns:
            Dictionary with user data or None
        """
        from app.modules.auth.models import User
        
        try:
            user = db.query(User).filter(User.phone == phone).first()
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "user": None
                }
            
            return {
                "success": True,
                "message": "User retrieved successfully",
                "user": UserAuthService.format_user_response(user)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving user: {str(e)}",
                "user": None
            }

    @staticmethod
    def get_all_users(db, skip: int = 0, limit: int = 100) -> Dict:
        """Get all users with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Number of records to return
            
        Returns:
            Dictionary with users list
        """
        from app.modules.auth.models import User
        
        try:
            users = db.query(User).offset(skip).limit(limit).all()
            total = db.query(User).count()
            
            return {
                "success": True,
                "message": "Users retrieved successfully",
                "users": [UserAuthService.format_user_response(u) for u in users],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving users: {str(e)}",
                "users": [],
                "total": 0
            }

    @staticmethod
    def update_user(db, user_id: str, **kwargs) -> Dict:
        """Update user information.
        
        Args:
            db: Database session
            user_id: User ID
            **kwargs: Fields to update (full_name, phone, is_active, is_verified, etc.)
            
        Returns:
            Dictionary with updated user data
        """
        from app.modules.auth.models import User
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "user": None
                }
            
            # Update allowed fields
            allowed_fields = ['full_name', 'phone', 'is_active', 'is_verified']
            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
                    setattr(user, key, value)
            
            db.commit()
            db.refresh(user)
            
            return {
                "success": True,
                "message": "User updated successfully",
                "user": UserAuthService.format_user_response(user)
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error updating user: {str(e)}",
                "user": None
            }

    @staticmethod
    def delete_user(db, user_id: str) -> Dict:
        """Delete a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary with success/failure message
        """
        from app.modules.auth.models import User
        
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
    def resend_otp(
        db,
        identifier: str,
        identifier_type: str  # 'email' or 'phone'
    ) -> Tuple[bool, str, Optional[str]]:
        """Resend OTP with validation checks.
        
        Checks:
        - OTP must exist and not be verified yet
        - Previous OTP must have expired or (remaining attempts >= 1)
        - User exists
        
        Args:
            db: Database session
            identifier: Email or phone
            identifier_type: Type of identifier
            
        Returns:
            Tuple of (success: bool, message: str, otp: Optional[str])
        """
        from app.modules.auth.models import User, OTPToken
        
        try:
            # Check if user exists
            if identifier_type == "email":
                user = db.query(User).filter(User.email == identifier).first()
            else:
                user = db.query(User).filter(User.phone == identifier).first()
            
            if not user:
                return False, "User not found", None
            
            # Check for existing unverified OTP
            existing_otp = db.query(OTPToken).filter(
                OTPToken.identifier == identifier,
                OTPToken.is_verified == False
            ).order_by(OTPToken.created_at.desc()).first()
            
            if existing_otp:
                # Check if OTP is still valid
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                remaining_ttl = _get_redis_client().ttl(OTPService._get_redis_key(identifier))
                
                if remaining_ttl > 0:
                    # OTP still exists in Redis - check if we can resend
                    otp_info = OTPService.get_otp_info(identifier)
                    remaining_attempts = 3 - otp_info.get("attempts", 0)
                    
                    if remaining_attempts <= 0:
                        # Too many attempts - OTP will expire naturally
                        return False, "Too many failed attempts. Please request a new OTP.", None
                    
                    # Check if enough time has passed since creation (e.g., 30 seconds)
                    created_at = datetime.fromisoformat(otp_info.get("created_at"))
                    time_elapsed = (now - created_at).total_seconds()
                    
                    if time_elapsed < 30:  # Wait at least 30 seconds before resend
                        return False, f"Please wait {int(30 - time_elapsed)} seconds before requesting another OTP", None
                
                else:
                    # OTP expired - delete the old record
                    db.delete(existing_otp)
                    db.commit()
            
            # Generate new OTP
            otp = OTPService.generate_numeric_otp()
            
            # Store in Redis
            otp_metadata = OTPService.store_otp(
                identifier=identifier,
                otp=otp,
                otp_type=OTPType.EMAIL if identifier_type == "email" else OTPType.SMS,
                expiry_minutes=2
            )
            
            # Create new OTP token record
            expires_at = datetime.utcnow() + timedelta(minutes=2)
            otp_token = OTPToken(
                user_id=user.id,
                identifier=identifier,
                otp_type=identifier_type,
                is_verified=False,
                verification_attempts=0,
                expires_at=expires_at
            )
            db.add(otp_token)
            db.commit()
            
            return True, "OTP resent successfully", otp
        
        except Exception as e:
            db.rollback()
            return False, f"Error resending OTP: {str(e)}", None
