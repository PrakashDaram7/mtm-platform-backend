

import json
import secrets
import string
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict
from enum import Enum

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.modules.auth.models import OTP, User

class OTPConfig:
    """Configuration for OTP generation and validation."""

    DEFAULT_LENGTH = 6  # 6-digit OTP
    DEFAULT_EXPIRY_MINUTES = 2  # OTP expires in 2 minutes
    DEFAULT_EXPIRY_SECONDS = DEFAULT_EXPIRY_MINUTES * 60
    MAX_ATTEMPTS = 3  # Maximum failed validation attempts
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    OTP_KEY_PREFIX = "otp:"  # Redis key prefix for OTPs
    USE_REDIS = True  # Set to False to disable Redis entirely
    FALLBACK_TO_DATABASE = True  # Fall back to database if Redis unavailable


class OTPType(str, Enum):
    """Types of OTP."""

    EMAIL = "email"
    SMS = "sms"
   


# Redis client initialization - Lazy loading to avoid startup failure
_redis_client = None
_redis_available = False


def _get_redis_client():
    """Get Redis client with lazy initialization and graceful error handling.
    
    Returns None if Redis is not available, allowing database fallback.
    """
    global _redis_client, _redis_available
    
    if not REDIS_AVAILABLE or not OTPConfig.USE_REDIS:
        return None
    
    if _redis_client is not None:
        return _redis_client
    
    if not _redis_available and not OTPConfig.FALLBACK_TO_DATABASE:
        return None
    
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
        _redis_available = True
        print(f"✓ Redis connection established at {OTPConfig.REDIS_HOST}:{OTPConfig.REDIS_PORT}")
        return _redis_client
    except Exception as e:
        _redis_available = False
        print(f"⚠ Redis unavailable at {OTPConfig.REDIS_HOST}:{OTPConfig.REDIS_PORT}")
        print(f"  Using database fallback for OTP storage")
        print(f"  For better performance, set up Redis or set USE_REDIS=False")
        return None


class OTPService:
    """Service for generating and managing OTPs using Redis (with database fallback)."""

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
        """Store an OTP with metadata in Redis (with database fallback).

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
        now = datetime.now(timezone.utc)
        expiry_time = now + timedelta(minutes=expiry_minutes)
        expiry_seconds = expiry_minutes * 60
        
        # Log OTP storage attempt
        print(f"🔐 Storing OTP for identifier: {identifier}, otp: {otp}, type: {otp_type.value}, expiry: {expiry_minutes} min")

        otp_data = {
            "otp": OTPService._hash_otp(otp),
            "otp_type": otp_type.value,
            "created_at": now.isoformat(),
            "expires_at": expiry_time.isoformat(),
            "attempts": 0,
            "verified": False,
        }

        redis_key = OTPService._get_redis_key(identifier)

        # Try to store in Redis if available
        redis_client = _get_redis_client()
        if redis_client:
            try:
                redis_client.setex(
                    name=redis_key,
                    time=expiry_seconds,
                    value=json.dumps(otp_data),
                )
                print(f"✅ OTP stored in Redis with key: {redis_key}")
            except Exception as e:
                print(f"⚠️ Failed to store OTP in Redis: {e}")
        else:
            print(f"⚠️ Redis not available, using database fallback only")

        # Always store in Database as fallback
        db = SessionLocal()
        try:
            # Always store both email and phone fields if available
            email_value = None
            phone_value = None
            if otp_type == OTPType.EMAIL:
                email_value = identifier
                phone_value = phone
            elif otp_type == OTPType.SMS:
                phone_value = identifier
                email_value = email_value if email_value else None
            else:
                # fallback, try to set both if possible
                email_value = email_value if email_value else None
                phone_value = phone if phone else None

            otp_record = OTP(
                user_id=user_id,
                email=email_value,
                phone=phone_value,
                otp_type=otp_type.value,
                otp_code=otp,  # Store unhashed OTP code for validation
                expires_at=expiry_time,
                is_used=False,
            )
            db.add(otp_record)
            db.commit()
            db.refresh(otp_record)
            print(f"✅ OTP stored in database with email: {email_value}, phone: {phone_value}, OTP ID: {otp_record.otp_id}")
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to store OTP in database: {e}")
            raise
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
        """Validate an OTP from Redis (with database fallback).

        Args:
            identifier: Unique identifier
            otp: The OTP to validate

        Returns:
            Tuple of (is_valid, message)
        """
        redis_client = _get_redis_client()
        
        # Try to validate from Redis first if available
        if redis_client:
            redis_key = OTPService._get_redis_key(identifier)
            try:
                otp_value = redis_client.get(redis_key)
                
                if otp_value:
                    otp_data = json.loads(otp_value)

                    # Check if OTP is already verified
                    if otp_data.get("verified"):
                        return False, "OTP has already been used."

                    # Check attempt limit
                    attempts = otp_data.get("attempts", 0)
                    if attempts >= OTPConfig.MAX_ATTEMPTS:
                        redis_client.delete(redis_key)
                        return False, "Too many failed attempts. Please request a new OTP."

                    # Validate OTP
                    hashed_input = OTPService._hash_otp(otp)
                    if hashed_input != otp_data["otp"]:
                        otp_data["attempts"] = attempts + 1
                        remaining = OTPConfig.MAX_ATTEMPTS - otp_data["attempts"]

                        # Update attempts in Redis while preserving TTL
                        ttl = redis_client.ttl(redis_key)
                        if ttl > 0:
                            redis_client.setex(
                                name=redis_key,
                                time=ttl,
                                value=json.dumps(otp_data),
                            )

                        return False, f"Invalid OTP. {remaining} attempts remaining."

                    # Mark as verified in Redis
                    otp_data["verified"] = True
                    otp_data["verified_at"] = datetime.now(timezone.utc).isoformat()

                    # Update in Redis
                    ttl = redis_client.ttl(redis_key)
                    if ttl > 0:
                        redis_client.setex(
                            name=redis_key,
                            time=ttl,
                            value=json.dumps(otp_data),
                        )

                    # Mark as used in Database
                    OTPService._mark_otp_as_used_in_db(identifier, otp)

                    return True, "OTP validated successfully."
            except Exception as e:
                print(f"Warning: Error validating OTP in Redis: {e}")
                # Fall through to database validation
        
        # Fallback to database validation
        return OTPService._validate_otp_from_db(identifier, otp)

    @staticmethod
    def _validate_otp_from_db(identifier: str, otp: str) -> Tuple[bool, str]:
        """Fallback validation from database when Redis is unavailable.

        Args:
            identifier: Unique identifier (email or phone)
            otp: The OTP to validate

        Returns:
            Tuple of (is_valid, message)
        """
        db = SessionLocal()
        try:
            # Use timezone-aware UTC datetime
            now_utc = datetime.now(timezone.utc)
            
            # Find the most recent, unused OTP for this phone/identifier
            print(f"🔍 Searching database for OTP with identifier: {identifier}, current time: {now_utc}")
            
            # Try to match by email or phone
            otp_record = db.query(OTP).filter(
                ((OTP.phone == identifier) | (OTP.email == identifier)),
                OTP.is_used == False
            ).order_by(OTP.created_at.desc()).first()

            if not otp_record:
                print(f"❌ No valid OTP found in database for identifier: {identifier}")
                # Debug: show all OTP records for this identifier
                all_records = db.query(OTP).filter((OTP.phone == identifier) | (OTP.email == identifier)).all()
                print(f"   Found {len(all_records)} total OTP records for {identifier}")
                for record in all_records:
                    try:
                        # Ensure expires_at is timezone-aware for comparison
                        expires_at = record.expires_at
                        if expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=timezone.utc)
                        expired = expires_at < now_utc if expires_at else True
                        print(f"   - OTP ID: {record.otp_id}, Code: {record.otp_code}, Used: {record.is_used}, Expired: {expired}, Expires at: {record.expires_at}")
                    except Exception as e:
                        print(f"   - OTP ID: {record.otp_id}, Error checking expiry: {str(e)}")
                return False, "OTP not found or expired. Please request a new OTP."

            # Check if OTP is expired - ensure timezone-aware comparison
            expires_at = otp_record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < now_utc:
                print(f"❌ OTP has expired at {expires_at}")
                return False, "OTP has expired. Please request a new OTP."

            # Validate OTP
            print(f"✅ Found OTP record in database. Validating...")
            print(f"   Stored OTP: {otp_record.otp_code}, Provided OTP: {otp}")
            
            if otp_record.otp_code != otp:
                print(f"❌ OTP mismatch. Expected: {otp_record.otp_code}, Got: {otp}")
                return False, "Invalid OTP."

            # Mark as used
            otp_record.is_used = True
            db.commit()
            print(f"✅ OTP validated and marked as used")

            return True, "OTP validated successfully."
        except Exception as e:
            db.rollback()
            print(f"❌ Error validating OTP from database: {str(e)}")
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
                ((OTP.phone == identifier) | (OTP.email == identifier)),
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
            now_utc = datetime.now(timezone.utc)
            otp_record = db.query(OTP).filter(
                ((OTP.phone == identifier) | (OTP.email == identifier))
            ).order_by(OTP.created_at.desc()).first()

            if otp_record:
                # Ensure expires_at is timezone-aware for comparison
                expires_at = otp_record.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                
                # Only return if not expired
                if expires_at > now_utc:
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

    @staticmethod
    def is_otp_verified(identifier: str) -> bool:
        """Check if an OTP is verified.

        Args:
            identifier: Unique identifier

        Returns:
            True if OTP is verified, False otherwise
        """
        redis_client = _get_redis_client()
        if not redis_client:
            return False
            
        redis_key = OTPService._get_redis_key(identifier)
        try:
            otp_value = redis_client.get(redis_key)

            if not otp_value:
                return False

            otp_data = json.loads(otp_value)
            return otp_data.get("verified", False)
        except Exception:
            return False

    @staticmethod
    def clear_otp(identifier: str) -> bool:
        """Clear an OTP from Redis (with database fallback).

        Args:
            identifier: Unique identifier

        Returns:
            True if OTP was cleared, False if not found
        """
        redis_client = _get_redis_client()
        if redis_client:
            redis_key = OTPService._get_redis_key(identifier)
            try:
                result = redis_client.delete(redis_key)
                return result > 0
            except Exception:
                pass
        
        # Fallback: Clear from database
        db = SessionLocal()
        try:
            db.query(OTP).filter((OTP.phone == identifier) | (OTP.email == identifier)).delete()
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def get_otp_info(identifier: str) -> Optional[Dict]:
        """Get OTP information (without revealing the actual OTP).

        Args:
            identifier: Unique identifier

        Returns:
            OTP metadata or None if not found
        """
        redis_client = _get_redis_client()
        if redis_client:
            redis_key = OTPService._get_redis_key(identifier)
            try:
                otp_value = redis_client.get(redis_key)

                if otp_value:
                    otp_data = json.loads(otp_value)
                    ttl = redis_client.ttl(redis_key)

                    return {
                        "otp_type": otp_data.get("otp_type"),
                        "created_at": otp_data.get("created_at"),
                        "expires_at": otp_data.get("expires_at"),
                        "verified": otp_data.get("verified"),
                        "attempts": otp_data.get("attempts"),
                        "ttl_seconds": ttl,
                    }
            except Exception:
                pass
        
        # Fallback to database
        db = SessionLocal()
        try:
            otp_record = db.query(OTP).filter(
                ((OTP.phone == identifier) | (OTP.email == identifier)),
                OTP.is_used == False
            ).order_by(OTP.created_at.desc()).first()
            
            if otp_record:
                ttl_seconds = max(0, int((otp_record.expires_at - datetime.now(timezone.utc)).total_seconds()))
                return {
                    "otp_type": "email",
                    "created_at": otp_record.created_at.isoformat(),
                    "expires_at": otp_record.expires_at.isoformat(),
                    "verified": otp_record.is_used,
                    "attempts": 0,
                    "ttl_seconds": ttl_seconds,
                }
        except Exception:
            pass
        finally:
            db.close()
        
        return None

    @staticmethod
    def get_remaining_ttl(identifier: str) -> Optional[int]:
        """Get remaining TTL for an OTP in seconds.

        Args:
            identifier: Unique identifier

        Returns:
            Remaining TTL in seconds, or None if OTP not found
        """
        redis_client = _get_redis_client()
        if redis_client:
            redis_key = OTPService._get_redis_key(identifier)
            try:
                ttl = redis_client.ttl(redis_key)
                return ttl if ttl > 0 else None
            except Exception:
                pass
        
        # Fallback to database
        db = SessionLocal()
        try:
            now_utc = datetime.now(timezone.utc)
            otp_record = db.query(OTP).filter(
                ((OTP.phone == identifier) | (OTP.email == identifier)),
                OTP.is_used == False,
                OTP.expires_at > now_utc
            ).first()
            
            if otp_record:
                ttl_seconds = int((otp_record.expires_at - now_utc).total_seconds())
                return ttl_seconds if ttl_seconds > 0 else None
        except Exception:
            pass
        finally:
            db.close()
        
        return None

    @staticmethod
    def get_redis_stats() -> Dict:
        """Get Redis stats for OTP storage (with database fallback).

        Returns:
            Dictionary containing OTP statistics
        """
        redis_client = _get_redis_client()
        if redis_client:
            try:
                pattern = f"{OTPConfig.OTP_KEY_PREFIX}*"
                otp_keys = redis_client.keys(pattern)

                verified_count = 0
                for key in otp_keys:
                    otp_value = redis_client.get(key)
                    if otp_value:
                        otp_data = json.loads(otp_value)
                        if otp_data.get("verified"):
                            verified_count += 1

                return {
                    "total_otps": len(otp_keys),
                    "verified_otps": verified_count,
                    "pending_otps": len(otp_keys) - verified_count,
                }
            except Exception:
                pass
        
        # Fallback to database statistics
        db = SessionLocal()
        try:
            total_otps = db.query(OTP).count()
            verified_otps = db.query(OTP).filter(OTP.is_used == True).count()
            pending_otps = total_otps - verified_otps
            
            return {
                "total_otps": total_otps,
                "verified_otps": verified_otps,
                "pending_otps": pending_otps,
            }
        except Exception:
            return {
                "total_otps": 0,
                "verified_otps": 0,
                "pending_otps": 0,
            }
        finally:
            db.close()


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
