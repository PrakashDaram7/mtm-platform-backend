# OTP Authentication API Documentation

## Overview

This document describes the OTP-based authentication endpoints for the MTM Platform Backend. The system uses Redis for temporary OTP storage and JWT tokens for session management.

---

## Features

✅ **6-digit numeric OTP generation**  
✅ **Secure OTP storage with Redis**  
✅ **Email and SMS support**  
✅ **JWT token generation on successful verification**  
✅ **Automatic user creation/retrieval**  
✅ **Rate limiting with max attempts (3)**  
✅ **OTP expiration (2 minutes)**  
✅ **Database audit trail**  
✅ **Clear error messages with remaining attempts**  

---

## Base URL

```
http://localhost:8000/api
```

---

## Endpoints

### 1. Send OTP

**Endpoint:** `POST /auth/send-otp`

**Description:** Send a 6-digit OTP to user's email or phone number.

**Request:**
```json
{
  "email": "user@example.com",
  "phone": null,
  "otp_type": "email"
}
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string (email format) | Conditional* | Email address to send OTP |
| `phone` | string | Conditional* | Phone number in international format (+1XXXXXXXXXX) |
| `otp_type` | string | Optional | Type of OTP: `email` or `sms` (default: `email`) |

*Either `email` XOR `phone` must be provided

**Success Response (200):**
```json
{
  "success": true,
  "message": "OTP sent successfully to email",
  "identifier": "us**@example.com",
  "expires_in_seconds": 120,
  "otp_type": "email"
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid phone number format"
}
```

**Error Response (500):**
```json
{
  "detail": "Failed to send OTP"
}
```

**Success Codes:**
- `200 OK` - OTP sent successfully

**Error Codes:**
- `400 Bad Request` - Invalid input (missing email/phone, invalid format)
- `429 Too Many Requests` - Rate limited
- `500 Internal Server Error` - Server error

**Example cURL:**
```bash
curl -X POST "http://localhost:8000/api/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp_type": "email"
  }'
```

**Console Output (for testing):**
```
==================================================
OTP for user@example.com: 123456
Expires in: 2 minutes
==================================================
```

---

### 2. Verify OTP

**Endpoint:** `POST /auth/verify-otp`

**Description:** Verify OTP and get JWT authentication token.

**Request:**
```json
{
  "email": "user@example.com",
  "phone": null,
  "otp": "123456"
}
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string (email format) | Conditional* | Email used for OTP |
| `phone` | string | Conditional* | Phone used for OTP |
| `otp` | string | Required | 6-digit OTP code |

*Either `email` XOR `phone` must match the one used in send-otp

**Success Response (200):**
```json
{
  "success": true,
  "message": "OTP verified successfully",
  "auth_token": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJKb2huIERvZSIsImlzX3ZlcmlmaWVkIjp0cnVlLCJleHAiOjE3Mzk0NzIxNDcsImlhdCI6MTczOTQ2ODU0N30.ABC123DEF456",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "is_verified": true
    }
  },
  "remaining_attempts": null
}
```

**Failure Response (401):**
```json
{
  "success": false,
  "message": "Invalid OTP. 2 attempts remaining.",
  "auth_token": null,
  "remaining_attempts": 2
}
```

**Error Response (400):**
```json
{
  "detail": "Either email or phone must be provided"
}
```

**Success Codes:**
- `200 OK` - OTP verified, token returned

**Error Codes:**
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Invalid OTP
- `500 Internal Server Error` - Server error

**Example cURL:**
```bash
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp": "123456"
  }'
```

---

### 3. Get OTP Status (Testing Only)

**Endpoint:** `GET /auth/otp-status/{identifier}`

**Description:** Check OTP status for an identifier (for testing/debugging).

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `identifier` | string | Email or phone to check OTP status |

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "otp_type": "email",
    "created_at": "2025-02-13T10:30:45.123456",
    "expires_at": "2025-02-13T10:32:45.123456",
    "verified": false,
    "attempts": 1,
    "ttl_seconds": 120
  }
}
```

**Error Response (404):**
```json
{
  "detail": "OTP not found"
}
```

**Example cURL:**
```bash
curl -X GET "http://localhost:8000/api/auth/otp-status/user@example.com"
```

---

### 4. Get Redis Statistics (Testing Only)

**Endpoint:** `GET /auth/redis-stats`

**Description:** Get Redis OTP storage statistics.

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "total_otps": 5,
    "verified_otps": 2,
    "pending_otps": 3
  }
}
```

**Example cURL:**
```bash
curl -X GET "http://localhost:8000/api/auth/redis-stats"
```

---

## Authentication Flow

### Step 1: Request OTP
```
POST /auth/send-otp
{
  "email": "user@example.com",
  "otp_type": "email"
}
```
**Response:** OTP sent to user's email (console output shows: `123456`)

### Step 2: Verify OTP
```
POST /auth/verify-otp
{
  "email": "user@example.com",
  "otp": "123456"
}
```
**Response:** JWT access token returned

### Step 3: Use Token
Include in subsequent requests:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## JWT Token Structure

The JWT token contains the following claims:

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_verified": true,
  "exp": 1739472147,
  "iat": 1739468547
}
```

**Token Details:**
- **Algorithm:** HS256
- **Secret Key:** Configurable via `SECRET_KEY` environment variable
- **Expiration:** Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 minutes)

---

## Configuration

### Environment Variables

```env
# JWT Configuration
SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Redis Configuration (in OTPConfig)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# MySQL Configuration
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=mtm_db
```

### OTP Configuration

Edit `app/modules/auth/services.py`:

```python
class OTPConfig:
    DEFAULT_LENGTH = 6              # OTP length
    DEFAULT_EXPIRY_MINUTES = 2      # Expiration time
    MAX_ATTEMPTS = 3                # Max failed attempts
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
```

---

## Error Handling

### Error Response Format

All errors follow this structure:

```json
{
  "detail": "Error message"
}
```

### Common Errors

| Error | Status | Cause |
|-------|--------|-------|
| Invalid phone number format | 400 | Phone doesn't match international format |
| Either email or phone must be provided | 400 | Both are null |
| OTP expired | 401 | OTP validity period exceeded |
| Invalid OTP | 401 | Wrong OTP code |
| Too many failed attempts | 429 | Exceeded max attempts |
| OTP has already been used | 401 | OTP was already verified |

---

## Security Considerations

### ✅ Implemented

1. **OTP Hashing**: OTPs are hashed with SHA256 before storage
2. **Input Validation**: Email and phone formats validated
3. **Rate Limiting**: Maximum 3 failed attempts per OTP
4. **Expiration**: OTPs expire after 2 minutes
5. **JWT Signing**: Access tokens signed with secret key
6. **Secure Storage**: OTPs stored in Redis with TTL
7. **Audit Trail**: OTP usage logged in database

### ⚠️ Todo for Production

1. **HTTPS**: Enable HTTPS in production
2. **CORS**: Restrict CORS origins
3. **Remove Debug Endpoints**: Remove `/otp-status` and `/redis-stats` endpoints
4. **Email/SMS Integration**: Implement actual email and SMS sending
5. **Rate Limiting Middleware**: Add global rate limiting
6. **Logging**: Implement comprehensive logging
7. **Secret Management**: Use secure secret management (e.g., AWS Secrets Manager)
8. **Database Encryption**: Encrypt sensitive fields

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id CHAR(36) PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(150) UNIQUE NOT NULL,
  phone VARCHAR(20) UNIQUE,
  password_hash VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  is_verified BOOLEAN DEFAULT FALSE,
  last_login DATETIME,
  role_id CHAR(36) FOREIGN KEY,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX (email),
  INDEX (phone),
  INDEX (is_active)
);
```

### OTP Tokens Table
```sql
CREATE TABLE otp_tokens (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) FOREIGN KEY NOT NULL,
  identifier VARCHAR(150) NOT NULL,
  otp_type VARCHAR(20) NOT NULL,
  is_verified BOOLEAN DEFAULT FALSE,
  verification_attempts INTEGER DEFAULT 0,
  verified_at DATETIME,
  expires_at DATETIME NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX (user_id),
  INDEX (identifier),
  INDEX (is_verified)
);
```

---

## Example Use Cases

### Case 1: New User Registration via Email
```bash
# Step 1: Send OTP
curl -X POST "http://localhost:8000/api/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com"}'

# Console shows: OTP = 456789

# Step 2: Verify OTP
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "otp": "456789"}'

# Returns JWT token - User is now logged in and verified
```

### Case 2: Phone-based OTP via SMS
```bash
# Step 1: Send OTP
curl -X POST "http://localhost:8000/api/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "otp_type": "sms"}'

# Step 2: Verify OTP
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "otp": "456789"}'
```

### Case 3: Wrong OTP - Retry
```bash
# Step 1: Send OTP
curl -X POST "http://localhost:8000/api/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
# OTP = 123456

# Step 2: Verify with wrong OTP (attempt 1)
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "otp": "000000"}'
# Returns: "Invalid OTP. 2 attempts remaining."

# Step 3: Verify with correct OTP (attempt 2)
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "otp": "123456"}'
# Success - Token returned
```

---

## Testing

### Prerequisites
- Redis running on `localhost:6379`
- MySQL running with configured database
- Python 3.8+

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Start Server
```bash
python main.py
```

### Test Endpoints
Use the cURL examples provided above or import collection into Postman.

---

## API Response Summary

| Endpoint | Method | Success | Error | Purpose |
|----------|--------|---------|-------|---------|
| `/auth/send-otp` | POST | 200 | 400, 500 | Send OTP |
| `/auth/verify-otp` | POST | 200 | 400, 401, 500 | Verify OTP & get token |
| `/auth/otp-status/{id}` | GET | 200 | 404, 500 | Check OTP status (test) |
| `/auth/redis-stats` | GET | 200 | 500 | Get Redis stats (test) |

---

## Support & Troubleshooting

### OTP not received?
- Check Redis connection: `redis-cli ping`
- Verify email/SMS service configuration
- Check console for OTP display (development mode)

### Token verification fails?
- Ensure `SECRET_KEY` matches on all instances
- Check token expiration: `exp` claim in JWT
- Verify `Authorization` header format: `Bearer {token}`

### Redis connection error?
```bash
# Start Redis
redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

### Database connection error?
- Verify MySQL credentials in `.env`
- Check database exists and is accessible
- Run migrations: `alembic upgrade head`

---

## Version History

- **v1.0.0** (2025-02-13) - Initial OTP authentication implementation
  - Send OTP via email/SMS
  - Verify OTP with JWT token generation
  - User auto-creation
  - Audit trail logging

---

## License

See [LICENSE](LICENSE) file for details.
