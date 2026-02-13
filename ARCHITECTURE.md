# OTP Authentication System Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client Application                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
    ┌─────────────┐            ┌──────────────┐
    │  Send OTP   │            │ Verify OTP   │
    │   Request   │            │  Request     │
    └─────────────┘            └──────────────┘
         │                           │
         │                           │
    ┌────▼──────────────────────────▼────┐
    │   FastAPI Route Handler             │
    │  (/api/auth/send-otp)               │
    │  (/api/auth/verify-otp)             │
    └────────┬─────────────────────────┬──┘
             │                         │
        ┌────▼─────┐            ┌─────▼────┐
        │  Validat │            │ OTPServi │
        │  ion     │            │ ce       │
        └────┬─────┘            └─────┬────┘
             │                        │
        ┌────▼────────────────────────▼─────┐
        │  Redis (OTP Storage)               │
        │  - OTP hashed (SHA256)            │
        │  - TTL 2 minutes                  │
        │  - Attempts tracking              │
        └────┬─────────────────────────────┬┘
             │                              │
        ┌────▼─────────────────────┐   ┌───▼──────────────────┐
        │ MySQL (Audit Trail)       │   │ JWT Token Generation │
        │ - OTPToken records        │   │ - Claims creation    │
        │ - User records            │   │ - HMAC-SHA256 sign   │
        │ - Verification log        │   └───┬──────────────────┘
        └──────────────────────────┘       │
                                           ▼
                                    ┌──────────────────┐
                                    │  JWT Token       │
                                    │  + User Data     │
                                    │  (Returned)      │
                                    └──────────────────┘
```

---

## Authentication Process Flow

### 1. Send OTP Flow
```
                    CLIENT
                      │
                      │ POST /api/auth/send-otp
                      │ { "email": "user@example.com" }
                      │
                      ▼
              ┌─────────────────┐
              │ FastAPI Handler │
              └────────┬────────┘
                       │
                   ┌───┴───────────────────────────────┐
                   │                                   │
                   ▼                                   ▼
        ┌────────────────────┐            ┌──────────────────────┐
        │ Input Validation   │            │ User Management      │
        │ - Check email/phone│            │ - Get/Create user    │
        │ - Validate format  │            │ - Store in MySQL     │
        └────────┬───────────┘            └────────┬─────────────┘
                 │                                  │
                 │                                  │
                 └──────────────┬───────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ OTPService            │
                    │ - Generate 6-digit OTP│
                    │ - Hash OTP (SHA256)   │
                    │ - Store in Redis      │
                    │ - Set TTL 2 min       │
                    └─────────┬─────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Redis               │
                    │ otp:email@ex.com    │
                    │ {                   │
                    │   hashed_otp: xxx   │
                    │   attempts: 0       │
                    │   verified: false   │
                    │ }                   │
                    │ TTL: 120 seconds    │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Console Output      │
                    │ OTP: 123456         │
                    │ (Development only)  │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ MySQL OTPToken Log  │
                    │ - user_id           │
                    │ - identifier        │
                    │ - otp_type          │
                    │ - created_at        │
                    │ - expires_at        │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ HTTP Response 200   │
                    │ {                   │
                    │   success: true,    │
                    │   identifier: us**  │
                    │   expires_in: 120   │
                    │ }                   │
                    └─────────────────────┘
```

### 2. Verify OTP Flow
```
                    CLIENT
                      │
                      │ POST /api/auth/verify-otp
                      │ { "email": "user@example.com", "otp": "123456" }
                      │
                      ▼
              ┌─────────────────┐
              │ FastAPI Handler │
              └────────┬────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ OTPService.validate  │
            │ - Get OTP from Redis │
            │ - Extract from JSON  │
            └───────┬──────────────┘
                    │
            ┌───────┴────────┬──────────┐
            │                │          │
            ▼                ▼          ▼
     ┌────────────┐  ┌──────────┐  ┌────────┐
     │ OTP Exists?│  │ Expired? │  │Too Many│
     │ No → Error │  │Yes→Error │  │Attempt?│
     └─────┬──────┘  └────┬─────┘  └───┬────┘
           │              │            │
           └──────────┬───┴────────┬───┘
                      │            │
                      ▼            ▼
              ┌────────────────┐  ┌──────────────┐
              │ Hash Input OTP │  │ Too Many→   │
              │ (SHA256)       │  │ Delete Redis │
              │ Compare Hash   │  │ Return Error │
              └─────┬──────────┘  └──────────────┘
                    │
            ┌───────┴────────────┐
            │                    │
            ▼                    ▼
     ┌────────────┐      ┌──────────────┐
     │ Match? ✓   │      │ No Match ✗   │
     │            │      │              │
     │ Mark as    │      │ Increment    │
     │ verified   │      │ attempts     │
     │ in Redis   │      │ Return error │
     │ in MySQL   │      │ + attempts   │
     │            │      │ remaining    │
     └─────┬──────┘      └──────────────┘
           │
           │
           ▼
    ┌──────────────────────┐
    │ Get/Create User      │
    │ from MySQL           │
    └────────┬─────────────┘
             │
             ▼
    ┌──────────────────────┐
    │ Update User          │
    │ - is_verified = TRUE │
    │ - last_login = now   │
    │ - Save to MySQL      │
    └────────┬─────────────┘
             │
             ▼
    ┌──────────────────────┐
    │ JWT Token Creation   │
    │ - Claims:            │
    │   sub: user_id       │
    │   email: user.email  │
    │   iat: now           │
    │   exp: now + 60min   │
    │ - Sign: HS256        │
    └────────┬─────────────┘
             │
             ▼
    ┌──────────────────────┐
    │ Clear OTP from Redis │
    │ (delete key)         │
    └────────┬─────────────┘
             │
             ▼
    ┌──────────────────────┐
    │ HTTP Response 200    │
    │ {                    │
    │   success: true,     │
    │   auth_token: {      │
    │     access_token: xx │
    │     token_type: bearer
    │     expires_in: 3600 │
    │     user: {...}      │
    │   }                  │
    │ }                    │
    └──────────────────────┘
```

---

## Component Interaction

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │           API Layer (FastAPI)                  │   │
│  │  ┌─────────────────────────────────────────┐  │   │
│  │  │ /api/auth/send-otp        (POST)        │  │   │
│  │  │ /api/auth/verify-otp      (POST)        │  │   │
│  │  │ /api/auth/otp-status/:id  (GET) [TEST]  │  │   │
│  │  │ /api/auth/redis-stats     (GET) [TEST]  │  │   │
│  │  └──────────┬──────────────────────────────┘  │   │
│  │             │                                  │   │
│  └─────────────┼──────────────────────────────────┘   │
│                │                                      │
│  ┌─────────────▼──────────────────────────────────┐   │
│  │        Service Layer                           │   │
│  │  ┌──────────────────────────────────────────┐ │   │
│  │  │ OTPService          UserAuthService      │ │   │
│  │  │ - generate_otp()    - validate_email() │ │   │
│  │  │ - store_otp()       - validate_phone() │ │   │
│  │  │ - validate_otp()    - format_response()│ │   │
│  │  │ - is_verified()     - normalize_phone()│ │   │
│  │  │ - clear_otp()                          │ │   │
│  │  │ - get_otp_info()                       │ │   │
│  │  │ - get_redis_stats()                    │ │   │
│  │  └──────────┬──────────────────────────┬────┘ │   │
│  └─────────────┼──────────────────────────┼──────┘   │
│                │                          │          │
│              ┌─▼──────┐           ┌──────▼─┐         │
│              │ Redis  │           │ MySQL  │         │
│              │ OTP    │           │ User   │         │
│              │Storage │           │Data    │         │
│              │(Cache) │           │(Audit) │         │
│              └────────┘           └────────┘         │
│                                                       │
│              ┌────────────────────────────────────┐  │
│              │  Security Layer (core/security.py) │  │
│              │  - create_access_token()          │  │
│              │  - verify_token()                 │  │
│              │  - decode_token()                 │  │
│              └────────────────────────────────────┘  │
│                                                       │
└─────────────────────────────────────────────────────┘
```

---

## Data Models

### User Model
```python
class User(Base):
    id: CHAR(36)                    # UUID Primary Key
    email: VARCHAR(150)             # Unique email
    phone: VARCHAR(20)              # Optional phone
    full_name: VARCHAR(100)         # User's name
    password_hash: VARCHAR(255)     # Optional password
    is_active: BOOLEAN = True       # Account status
    is_verified: BOOLEAN = False    # OTP verification status
    last_login: DATETIME            # Last login timestamp
    role_id: CHAR(36) FK            # Role reference
    created_at: DATETIME            # Creation timestamp
    updated_at: DATETIME            # Update timestamp
    
    Relationships:
    - role: Role (many-to-one)
    - otp_tokens: OTPToken (one-to-many)
```

### OTPToken Model
```python
class OTPToken(Base):
    id: CHAR(36)                    # UUID Primary Key
    user_id: CHAR(36) FK            # User reference
    identifier: VARCHAR(150)        # Email or phone
    otp_type: VARCHAR(20)          # 'email' or 'sms'
    is_verified: BOOLEAN = False    # Verification status
    verification_attempts: INT = 0  # Failed attempt count
    verified_at: DATETIME           # Verification timestamp
    expires_at: DATETIME            # OTP expiration
    created_at: DATETIME            # Creation timestamp
    
    Relationships:
    - user: User (many-to-one)
```

### Redis OTP Storage
```json
{
  "key": "otp:user@example.com",
  "value": {
    "otp": "sha256_hash_value",
    "otp_type": "email",
    "created_at": "2025-02-13T10:30:45.123456",
    "expires_at": "2025-02-13T10:32:45.123456",
    "attempts": 0,
    "verified": false
  },
  "ttl": 120  # seconds
}
```

---

## JWT Token Structure

### Token Claims
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_verified": true,
  "iat": 1739468547,
  "exp": 1739472147
}
```

### Token Encoding
- **Algorithm:** HS256 (HMAC with SHA-256)
- **Secret:** Configurable via `SECRET_KEY`
- **Expiration:** `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60)

---

## Error Handling Flow

```
                  Request
                    │
                    ▼
        ┌──────────────────────┐
        │ Input Validation     │
        └─────┬────────────────┘
              │
         ┌────┴────┐
         │          │
         ▼          ▼
      Valid      Invalid
        │          │
        │          └──→ HTTP 400 Bad Request
        │
        ▼
    ┌──────────────────────┐
    │ OTP Operation        │
    └─────┬────────────────┘
          │
     ┌────┴─────────────┬──────┐
     │                  │      │
     ▼                  ▼      ▼
  Success          Expired  Not Found
     │               │        │
     │               ▼        │
     │          HTTP 401      │
     │          "Expired"     │
     │                        │
     │                    HTTP 401
     │                    "Not Found"
     │
     ▼
 HTTP 200
 Token Returned
```

---

## Security Architecture

```
┌────────────────────────────────────────────────────┐
│              Security Layers                        │
├────────────────────────────────────────────────────┤
│                                                    │
│ Layer 1: Input Validation                          │
│ ├─ Email format validation                         │
│ ├─ Phone format validation                         │
│ └─ OTP format validation                           │
│                                                    │
│ Layer 2: OTP Generation & Storage                  │
│ ├─ Cryptographically secure random (secrets)       │
│ ├─ SHA256 hashing before storage                   │
│ ├─ Redis TTL expiration (2 min)                    │
│ └─ Rate limiting (3 attempts max)                  │
│                                                    │
│ Layer 3: Verification & Comparison                 │
│ ├─ Hash-based comparison (timing-safe)             │
│ ├─ Attempt counter                                 │
│ ├─ Expiration check                                │
│ └─ One-time use (mark as verified)                │
│                                                    │
│ Layer 4: Token Generation                          │
│ ├─ JWT with HMAC-SHA256                            │
│ ├─ Configurable expiration                         │
│ ├─ User claims in token                            │
│ └─ Server-side signature verification              │
│                                                    │
│ Layer 5: Audit & Logging                           │
│ ├─ Database audit trail                            │
│ ├─ OTP attempt logging                             │
│ ├─ Verification timestamp                          │
│ └─ User identification                             │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## Request/Response Flow Example

### Successful Flow
```
Client Request:
POST /api/auth/send-otp
{
  "email": "user@example.com",
  "otp_type": "email"
}
                    │
                    ▼
Server Processing:
1. Validate email format ✓
2. Generate 6-digit OTP (123456)
3. Hash OTP with SHA256
4. Store in Redis with TTL 120s
5. Create OTPToken record in MySQL
6. Log to console (dev only)
                    │
                    ▼
Server Response:
HTTP 200 OK
{
  "success": true,
  "message": "OTP sent successfully to email",
  "identifier": "us**@example.com",
  "expires_in_seconds": 120,
  "otp_type": "email"
}

User Input OTP: 123456
                    │
                    ▼
Client Request:
POST /api/auth/verify-otp
{
  "email": "user@example.com",
  "otp": "123456"
}
                    │
                    ▼
Server Processing:
1. Get OTP from Redis ✓
2. Check not expired ✓
3. Check not verified yet ✓
4. Check attempts < 3 ✓
5. Hash input "123456" → matches stored hash ✓
6. Mark as verified in Redis
7. Create/Update user in MySQL
8. Set is_verified = true, last_login = now
9. Generate JWT token
10. Clear OTP from Redis
                    │
                    ▼
Server Response:
HTTP 200 OK
{
  "success": true,
  "message": "OTP verified successfully",
  "auth_token": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "is_verified": true
    }
  }
}
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Production                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         Load Balancer / Reverse Proxy         │  │
│  │ (nginx / AWS ALB / CloudFlare)                │  │
│  └──────────────────┬───────────────────────────┘  │
│                     │                              │
│          ┌──────────┴──────────┐                   │
│          │                     │                   │
│  ┌───────▼─────┐      ┌───────▼─────┐            │
│  │ FastAPI     │      │ FastAPI     │            │
│  │ Server 1    │      │ Server 2    │            │
│  │ (Region A)  │      │ (Region B)  │            │
│  └───────┬─────┘      └───────┬─────┘            │
│          │                     │                   │
│          └──────────┬──────────┘                   │
│                     │                              │
│          ┌──────────┴──────────┬──────────┐       │
│          │                     │          │        │
│  ┌───────▼──────┐      ┌──────▼────┐   ┌▼────┐  │
│  │ Redis Cache  │      │ MySQL DB  │   │Logs │  │
│  │ (Cluster)    │      │(Replicated)   │ &  │  │
│  └──────────────┘      └───────────┘   │Mon │  │
│                                        │itor│  │
│                                        └────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Monitoring & Observability

```
┌─────────────────────────────────────────┐
│         Monitoring Metrics              │
├─────────────────────────────────────────┤
│                                         │
│ • OTP Generation Rate                   │
│ • Verification Success/Failure Rate     │
│ • Average Verification Time             │
│ • Failed Attempts                       │
│ • Token Generation Rate                 │
│ • API Response Times                    │
│ • Redis Operations Latency              │
│ • Database Query Performance            │
│ • User Creation Rate                    │
│ • Error Rates by Type                   │
│ • Active OTP Count                      │
│ • JWT Token Expiration Events           │
│                                         │
└─────────────────────────────────────────┘
```

---

**This architecture ensures:**
- ✅ Scalability (stateless API, Redis cache)
- ✅ Security (hashed OTPs, JWT tokens, rate limiting)
- ✅ Reliability (database audit trail, error handling)
- ✅ Maintainability (separated concerns, service layer)
- ✅ Observability (logging, metrics, monitoring)
