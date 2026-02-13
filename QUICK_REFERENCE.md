# OTP Authentication - Quick Reference & Troubleshooting

## 🚀 Quick Start (5 minutes)

### 1. Required Services Running

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: MySQL
mysql -u root -p

# Terminal 3: FastAPI
cd c:\Users\Admin\OneDrive\Documents\GitHub\mtm-platform-backend
python main.py
```

**Expected Output:**
```
==================================================
Server Startup Check:
Status: SUCCESS
Message: [database connection details]
==================================================

OTP Auth API running at http://localhost:8000
Swagger Docs: http://localhost:8000/docs
```

---

## 📋 Common Workflows

### Workflow 1: Email-based OTP Login

```bash
# Step 1: Request OTP
curl -X POST "http://localhost:8000/api/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "otp_type": "email"
  }'

# Response:
# {
#   "success": true,
#   "message": "OTP sent successfully to email",
#   "identifier": "jo**@example.com",
#   "expires_in_seconds": 120,
#   "otp_type": "email"
# }

# Console shows: OTP = 123456

# Step 2: Verify OTP
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "otp": "123456"
  }'

# Response:
# {
#   "success": true,
#   "message": "OTP verified successfully",
#   "auth_token": {
#     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#     "token_type": "bearer",
#     "expires_in": 3600,
#     "user": {
#       "id": "550e8400-e29b-41d4-a716-446655440000",
#       "email": "john@example.com",
#       "full_name": "john@example.com",
#       "is_verified": true
#     }
#   }
# }

# Step 3: Use Token in Requests
curl -X GET "http://localhost:8000/api/protected" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Workflow 2: Phone-based OTP Login (SMS)

```bash
# Step 1: Request OTP
curl -X POST "http://localhost:8000/api/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "otp_type": "sms"
  }'

# Step 2: Verify OTP
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "otp": "123456"
  }'
```

### Workflow 3: Retry After Failed Attempt

```bash
# Step 1: Send OTP
curl -X POST "http://localhost:8000/api/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# OTP = 123456

# Step 2: Wrong OTP (Attempt 1)
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "otp": "000000"}'

# Response:
# {
#   "success": false,
#   "message": "Invalid OTP. 2 attempts remaining.",
#   "auth_token": null,
#   "remaining_attempts": 2
# }

# Step 3: Wrong OTP (Attempt 2)
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "otp": "111111"}'

# Response:
# {
#   "success": false,
#   "message": "Invalid OTP. 1 attempts remaining.",
#   "auth_token": null,
#   "remaining_attempts": 1
# }

# Step 4: Correct OTP (Attempt 3)
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "otp": "123456"}'

# Success! Token returned
```

---

## 🧪 Testing Endpoints with Postman

### Collection Setup

1. **Create New Collection:** "OTP Authentication"

2. **Environment Variables:**
```json
{
  "base_url": "http://localhost:8000/api",
  "email": "test@example.com",
  "phone": "+1234567890",
  "otp": "123456",
  "token": ""
}
```

3. **Request 1: Send OTP (Email)**
```
Method: POST
URL: {{base_url}}/auth/send-otp
Header: Content-Type: application/json
Body (raw):
{
  "email": "{{email}}",
  "otp_type": "email"
}
```

4. **Request 2: Verify OTP**
```
Method: POST
URL: {{base_url}}/auth/verify-otp
Header: Content-Type: application/json
Body (raw):
{
  "email": "{{email}}",
  "otp": "{{otp}}"
}
```

5. **Request 3: Check OTP Status**
```
Method: GET
URL: {{base_url}}/auth/otp-status/{{email}}
```

6. **Request 4: Redis Stats**
```
Method: GET
URL: {{base_url}}/auth/redis-stats
```

---

## 🔍 Debugging & Troubleshooting

### Issue 1: "Failed to connect to Redis"

**Symptoms:**
```
RuntimeError: Failed to connect to Redis: [Errno 111] Connection refused
```

**Solutions:**
```bash
# Check if Redis is installed
redis-cli --version

# Start Redis
redis-server

# Test connection
redis-cli ping
# Should return: PONG

# Check Redis on Windows
# Using WSL or Docker:
wsl redis-server
# OR
docker run -d -p 6379:6379 redis:latest
```

### Issue 2: "Failed to connect to MySQL database"

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (1045, "Access denied for user 'root'@'localhost'")
```

**Solutions:**
```bash
# Check .env file variables
echo $MYSQL_USER
echo $MYSQL_PASSWORD
echo $MYSQL_HOST

# Test MySQL connection
mysql -u root -p
# Enter password

# Verify database exists
SHOW DATABASES;

# Update .env if needed
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=mtm_db
```

### Issue 3: "OTP not found" error

**Symptoms:**
```json
{
  "detail": "OTP not found. Please request a new OTP."
}
```

**Causes & Solutions:**
```
1. Redis expired the OTP (TTL 2 minutes)
   → Send OTP again

2. OTP was already verified
   → Request new OTP

3. Redis connection issue
   → Check Redis running: redis-cli ping

4. Wrong identifier
   → Make sure you use same email/phone in verify
```

### Issue 4: "Too many failed attempts"

**Symptoms:**
```json
{
  "detail": "Too many failed attempts. Please request a new OTP."
}
```

**Causes & Solutions:**
```
1. You tried wrong OTP 3 times
   → Request new OTP with send-otp endpoint

2. Check remaining attempts in response
   → Each wrong attempt shows how many left

3. Clear OTP manually in Redis:
   redis-cli DEL "otp:user@example.com"
```

### Issue 5: "JWT decode error"

**Symptoms:**
```
jwt.exceptions.DecodeError: Signature verification failed
```

**Causes & Solutions:**
```
1. SECRET_KEY mismatch
   → Same SECRET_KEY must be used for signing/verifying

2. Token expired
   → Check 'exp' claim in JWT

3. Corrupted token
   → Request new authentication

4. Verify in .env:
   SECRET_KEY=your-secret-key-change-in-production
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### Issue 6: "Invalid phone number format"

**Symptoms:**
```json
{
  "detail": "Invalid phone number format"
}
```

**Valid Formats:**
```
✓ +1234567890
✓ +1 (234) 567-8900
✓ +1-234-567-8900
✓ +1 234 567 8900
✓ 1234567890
✓ (234) 567-8900

✗ 123456
✗ abc1234567
✗ +1234
```

### Issue 7: Empty "identifier" in response

**Expected:**
```json
{
  "identifier": "us**@example.com"
}
```

**Troubleshooting:**
```
1. Check email is actually provided
2. Verify email format is valid
3. Check schemas.py mask_identifier function
4. Look at routes.py send_otp endpoint
```

---

## 🛠️ Development Helpers

### Check OTP in Console (Development)

```
When sending OTP, check server console:

==================================================
OTP for user@example.com: 123456
Expires in: 2 minutes
==================================================

Use this OTP for verification.
```

### View OTP Status (Testing)

```bash
curl -X GET "http://localhost:8000/api/auth/otp-status/user@example.com"

# Response:
# {
#   "success": true,
#   "data": {
#     "otp_type": "email",
#     "created_at": "2025-02-13T10:30:45.123456",
#     "expires_at": "2025-02-13T10:32:45.123456",
#     "verified": false,
#     "attempts": 1,
#     "ttl_seconds": 120
#   }
# }
```

### Check Redis Storage

```bash
# Connect to Redis
redis-cli

# List all OTP keys
KEYS "otp:*"

# View specific OTP
GET "otp:user@example.com"

# View TTL
TTL "otp:user@example.com"

# Clear all OTPs
FLUSHDB

# Exit
EXIT
```

### Decode JWT Token

```bash
# Using Python
python -c "
import jwt
import json
import base64

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
# Remove 'Bearer ' if present
parts = token.split('.')

# Decode payload (part 2)
payload = parts[1]
# Add padding if needed
padding = 4 - len(payload) % 4
if padding != 4:
    payload += '=' * padding

decoded = base64.urlsafe_b64decode(payload)
print(json.dumps(json.loads(decoded), indent=2))
"

# Online: https://jwt.io
```

### Query OTP Tokens from Database

```sql
-- List recent OTPs
SELECT * FROM otp_tokens 
ORDER BY created_at DESC 
LIMIT 10;

-- Check verified OTPs
SELECT * FROM otp_tokens 
WHERE is_verified = 1
ORDER BY verified_at DESC;

-- Check failed attempts
SELECT identifier, verification_attempts 
FROM otp_tokens 
WHERE is_verified = 0
ORDER BY created_at DESC;

-- User with most verified OTPs
SELECT u.id, u.email, COUNT(*) as verified_count
FROM users u
JOIN otp_tokens o ON u.id = o.user_id
WHERE o.is_verified = 1
GROUP BY u.id
ORDER BY verified_count DESC;
```

---

## 📊 Monitoring Commands

### Check System Health

```bash
# Redis Health
redis-cli PING              # Should return PONG
redis-cli INFO              # Full server info
redis-cli DBSIZE            # Number of keys

# MySQL Health
mysql -u root -p -e "SELECT 1"
mysql -u root -p -e "SELECT COUNT(*) as user_count FROM users"
mysql -u root -p -e "SELECT COUNT(*) as otp_count FROM otp_tokens"

# FastAPI Server Health
curl http://localhost:8000/health
```

### Performance Metrics

```bash
# Redis Stats
curl http://localhost:8000/api/auth/redis-stats

# Database Stats
mysql -u root -p << EOF
SELECT 
  (SELECT COUNT(*) FROM users) as total_users,
  (SELECT COUNT(*) FROM otp_tokens) as total_otps,
  (SELECT COUNT(*) FROM otp_tokens WHERE is_verified = 1) as verified_otps,
  (SELECT COUNT(*) FROM otp_tokens WHERE is_verified = 0) as pending_otps;
EOF
```

---

## 🔐 Security Checklist

### Before Production Deployment

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Change `MYSQL_PASSWORD` in `.env`
- [ ] Enable HTTPS (use SSL certificates)
- [ ] Set `DEBUG = False` in FastAPI
- [ ] Restrict CORS origins
- [ ] Remove or protect `/otp-status` endpoint
- [ ] Remove or protect `/redis-stats` endpoint
- [ ] Implement actual email sending (SMTP)
- [ ] Implement actual SMS sending (Twilio/AWS SNS)
- [ ] Add rate limiting middleware
- [ ] Add logging and monitoring
- [ ] Use secrets management (AWS Secrets Manager)
- [ ] Enable database encryption
- [ ] Set up Redis password/authentication
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS for database
- [ ] Enable query logging for audit
- [ ] Set up backup strategy

---

## 📝 Configuration Checklist

### Required Environment Variables (.env)

```env
# ✓ REQUIRED
SECRET_KEY=your-very-secret-key-1234567890
MYSQL_USER=root
MYSQL_PASSWORD=your-db-password
MYSQL_DATABASE=mtm_db

# Optional (Defaults provided)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
MYSQL_HOST=localhost
MYSQL_PORT=3306
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Verify Configuration

```bash
# Check if .env exists
ls -la .env

# Verify environment variables are loaded
python -c "
from app.core.config import *
from app.core.security import *
print('MySQL:', MYSQL_HOST, MYSQL_PORT)
print('Database:', MYSQL_DATABASE)
print('JWT Algorithm:', ALGORITHM)
print('Token Expiry:', ACCESS_TOKEN_EXPIRE_MINUTES, 'minutes')
"
```

---

## 🚀 Performance Tips

### Optimization Strategies

```python
# 1. Redis Connection Pooling
redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50
)

# 2. Database Connection Pooling (SQLAlchemy)
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40
)

# 3. Enable Redis Pipelining
# Multiple commands in one round trip

# 4. Implement caching layer
# Cache user objects after first lookup

# 5. Use database indexes
# Already configured on:
# - users.email
# - users.phone
# - users.is_active
# - otp_tokens.user_id
# - otp_tokens.identifier
# - otp_tokens.is_verified
```

---

## 📞 Support Contacts

| Issue Type | Action |
|-----------|--------|
| API Not Responding | Check if FastAPI server is running |
| Redis Error | Check `redis-cli ping` |
| Database Error | Check MySQL connection with credentials |
| OTP Not Received | Check console output in development mode |
| Token Invalid | Check SECRET_KEY matches |
| CORS Error | Check CORS configuration in main.py |

---

## 📚 Quick Links

- [Full API Documentation](OTP_AUTH_API_DOCUMENTATION.md)
- [Architecture & Diagrams](ARCHITECTURE.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [JWT Documentation](https://tools.ietf.org/html/rfc7519)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Redis Documentation](https://redis.io/documentation)

---

**Last Updated:** February 13, 2025
