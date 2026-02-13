

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
   


# Redis client initialization
try:
    _redis_client = redis.Redis(
        host=OTPConfig.REDIS_HOST,
        port=OTPConfig.REDIS_PORT,
        db=OTPConfig.REDIS_DB,
        decode_responses=True,
    )
    # Test connection
    _redis_client.ping()
except Exception as e:
    raise RuntimeError(f"Failed to connect to Redis: {e}")


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
        _redis_client.setex(
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
        otp_value = _redis_client.get(redis_key)

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
            _redis_client.delete(redis_key)
            return False, "Too many failed attempts. Please request a new OTP."

        # Validate OTP
        hashed_input = OTPService._hash_otp(otp)
        if hashed_input != otp_data["otp"]:
            otp_data["attempts"] = attempts + 1
            remaining = OTPConfig.MAX_ATTEMPTS - otp_data["attempts"]

            # Update attempts in Redis while preserving TTL
            ttl = _redis_client.ttl(redis_key)
            if ttl > 0:
                _redis_client.setex(
                    name=redis_key,
                    time=ttl,
                    value=json.dumps(otp_data),
                )

            return False, f"Invalid OTP. {remaining} attempts remaining."

        # Mark as verified in Redis
        otp_data["verified"] = True
        otp_data["verified_at"] = datetime.utcnow().isoformat()

        # Update in Redis
        ttl = _redis_client.ttl(redis_key)
        if ttl > 0:
            _redis_client.setex(
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
        otp_value = _redis_client.get(redis_key)

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
        result = _redis_client.delete(redis_key)
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
        otp_value = _redis_client.get(redis_key)

        if not otp_value:
            return None

        otp_data = json.loads(otp_value)
        ttl = _redis_client.ttl(redis_key)

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
        ttl = _redis_client.ttl(redis_key)
        return ttl if ttl > 0 else None

    @staticmethod
    def get_redis_stats() -> Dict:
        """Get Redis stats for OTP storage.

        Returns:
            Dictionary containing Redis statistics
        """
        pattern = f"{OTPConfig.OTP_KEY_PREFIX}*"
        otp_keys = _redis_client.keys(pattern)

        verified_count = 0
        for key in otp_keys:
            otp_value = _redis_client.get(key)
            if otp_value:
                otp_data = json.loads(otp_value)
                if otp_data.get("verified"):
                    verified_count += 1

        return {
            "total_otps": len(otp_keys),
            "verified_otps": verified_count,
            "pending_otps": len(otp_keys) - verified_count,
        }

    @staticmethod
    def cleanup_expired_otps_from_db() -> int:
        """Clean up expired OTPs from database.

        Returns:
            Number of expired OTPs deleted
        """
        db = SessionLocal()
        try:
            # Delete expired OTPs older than 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            deleted = db.query(OTP).filter(OTP.expires_at < cutoff_date).delete()
            db.commit()
            return deleted
        except Exception as e:
            db.rollback()
            print(f"Warning: Failed to cleanup expired OTPs: {e}")
            return 0
        finally:
            db.close()

    @staticmethod
    def get_db_stats() -> Dict:
        """Get database stats for OTP storage.

        Returns:
            Dictionary containing database OTP statistics
        """
        db = SessionLocal()
        try:
            total_otps = db.query(OTP).count()
            used_otps = db.query(OTP).filter(OTP.is_used == True).count()
            pending_otps = db.query(OTP).filter(OTP.is_used == False).count()
            expired_otps = db.query(OTP).filter(OTP.expires_at < datetime.utcnow()).count()

            return {
                "total_otps": total_otps,
                "used_otps": used_otps,
                "pending_otps": pending_otps,
                "expired_otps": expired_otps,
            }
        except Exception as e:
            print(f"Warning: Failed to get database stats: {e}")
            return {}
        finally:
            db.close()
