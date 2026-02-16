# MTM Platform Backend - Authentication & RBAC System Documentation

## Overview

The MTM Platform Backend features a complete authentication and role-based access control (RBAC) system with the following capabilities:

- **JWT-based Authentication**: Secure access token and refresh token system
- **Role-Based Access Control (RBAC)**: Fine-grained permission management
- **Password Hashing**: Using bcrypt for secure password storage
- **User Verification**: Support for verified and unverified users
- **Permission Management**: Granular control over resource access

## System Architecture

### Components

1. **Security Module** (`app/core/security.py`)
   - JWT token creation and verification
   - Password hashing and verification
   - User authentication functions
   - RBAC service for permission checks

2. **RBAC Middleware** (`app/core/rbac_middleware.py`)
   - Role and permission verification
   - Custom FastAPI dependencies for access control

3. **Authentication Routes** (`app/modules/auth/routes.py`)
   - User registration and login
   - Token refresh
   - User profile management
   - Admin controls

4. **Test Routes** (`app/modules/test/routes.py`)
   - Sample endpoints for different roles
   - RBAC functionality demonstrations

## Database Models

### Roles
```
Role
  ├── role_id (UUID)
  ├── role_name (string) - e.g., "admin", "moderator", "user"
  ├── description (text)
  ├── is_active (boolean)
  └── Relationships:
      ├── users (One-to-Many)
      └── permissions (One-to-Many)
```

### Users
```
User
  ├── id (UUID)
  ├── full_name (string)
  ├── email (string) - unique
  ├── phone (string) - optional
  ├── password_hash (string) - bcrypt hashed
  ├── is_active (boolean)
  ├── is_verified (boolean)
  ├── role_id (UUID) - Foreign Key to Role
  ├── last_login (datetime)
  └── Relationships:
      └── role (Many-to-One)
```

### Permissions
```
Permission
  ├── permission_id (UUID)
  ├── permission_name (string)
  ├── resource (string) - e.g., "users", "events", "payments"
  ├── action (string) - e.g., "create", "read", "update", "delete"
  ├── description (text)
  └── role_id (UUID) - Foreign Key to Role
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

The `.env` file is already configured with:
- MySQL database credentials
- JWT secret key
- Token expiration settings
- Redis configuration (for OTP)

### 3. Initialize Database with Sample Data

```bash
python seed.py
```

This will create:
- **5 Default Roles**: admin, moderator, organizer, member, user
- **5 Sample Users** with different roles
- **Permissions** mapped to roles

#### Sample User Credentials:
```
Admin:      admin@mtm.com / admin123
Moderator:  moderator@mtm.com / moderator123
Organizer:  organizer@mtm.com / organizer123
Member:     member@mtm.com / member123
User:       user@mtm.com / user123
```

### 4. Start the Server

```bash
python main.py
```

Server will start at: `http://0.0.0.0:8000`

**API Documentation**: `http://localhost:8000/docs`

## API Endpoints

### Authentication Endpoints

#### 1. Register New User
```
POST /api/auth/register
Body: {
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "password": "securepass123"
}
```

**Response**:
```json
{
  "id": "user-uuid",
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "is_active": true,
  "is_verified": false,
  "role_name": "user"
}
```

#### 2. Login User
```
POST /api/auth/login
Body: {
  "email": "admin@mtm.com",
  "password": "admin123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### 3. Get Current User Info
```
GET /api/auth/me
Headers: Authorization: Bearer <access_token>
```

#### 4. Refresh Access Token
```
POST /api/auth/refresh
Body: {
  "refresh_token": "eyJhbGc..."
}
```

#### 5. Change Password
```
POST /api/auth/change-password
Headers: Authorization: Bearer <access_token>
Body: {
  "current_password": "admin123",
  "new_password": "newpassword123",
  "confirm_password": "newpassword123"
}
```

### RBAC Management Endpoints (Admin Only)

#### List All Users
```
GET /api/auth/users?skip=0&limit=10
Headers: Authorization: Bearer <admin_token>
```

#### Update User Role
```
PUT /api/auth/users/{user_id}/role
Headers: Authorization: Bearer <admin_token>
Body: {
  "role_name": "moderator"
}
```

#### Disable User Account
```
POST /api/auth/users/{user_id}/disable
Headers: Authorization: Bearer <admin_token>
```

#### Enable User Account
```
POST /api/auth/users/{user_id}/enable
Headers: Authorization: Bearer <admin_token>
```

### Test/Demo Endpoints

#### Public Information
```
GET /api/test/public/info
```

#### User Dashboard (Authenticated)
```
GET /api/test/user/dashboard
Headers: Authorization: Bearer <access_token>
```

#### User Permissions
```
GET /api/test/user/permissions
Headers: Authorization: Bearer <access_token>
```

#### Moderator Dashboard (Moderator/Admin Only)
```
GET /api/test/moderator/dashboard
Headers: Authorization: Bearer <moderator_token>
```

#### Admin Dashboard (Admin Only)
```
GET /api/test/admin/dashboard
Headers: Authorization: Bearer <admin_token>
```

#### System Statistics (Admin Only)
```
GET /api/test/admin/system-stats
Headers: Authorization: Bearer <admin_token>
```

#### Test Role Check
```
GET /api/test/test/role-check/{user_id}
Headers: Authorization: Bearer <admin_token>
```

#### Test Permission Check
```
GET /api/test/test/permission-check/{resource}/{action}
Headers: Authorization: Bearer <access_token>
```

## Role Hierarchy and Permissions

### Admin Role
- Full system access
- Can create, read, update, delete users
- Can assign roles
- Can disable/enable user accounts
- Can view system statistics
- Can manage moderators

### Moderator Role
- Can view user list
- Can flag users for review
- Can moderate content
- Can send notifications

### Organizer Role
- Can create events
- Can read/update own events
- Can manage event details

### Member Role
- Can read user profiles
- Can update own profile
- Can participate in events

### User Role
- Can read own profile
- Can update own profile
- Basic access to platform

## Testing the System

### Using curl Commands

#### 1. Register a New User
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

#### 2. Login
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mtm.com",
    "password": "admin123"
  }'
```

#### 3. Access Protected Endpoint
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 4. Test Role-Based Access
```bash
# This will succeed with admin token
curl -X GET "http://localhost:8000/api/test/admin/dashboard" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# This will fail with regular user token
curl -X GET "http://localhost:8000/api/test/admin/dashboard" \
  -H "Authorization: Bearer USER_TOKEN"
```

### Using Swagger UI

1. Open `http://localhost:8000/docs` in your browser
2. Click the "Authorize" button
3. Enter your Bearer token
4. Test endpoints directly from the UI

## Security Features

### 1. Password Security
- Passwords are hashed using bcrypt
- Salted hashing prevents rainbow table attacks
- Password verification is time-safe

### 2. Token Security
- JWT tokens with expiration
- Separate access and refresh tokens
- Access tokens expire in 30 minutes
- Refresh tokens expire in 7 days
- Secret key is environment-protected

### 3. Authorization
- Token validation on every protected request
- Role checking before action execution
- Permission-based access control
- Account status verification (active/disabled)

## Troubleshooting

### Database Connection Issues
```
⚠️  Failed to connect to MySQL
Solution: Verify MySQL is running and credentials in .env are correct
```

### Token Expired
```
Error: "Could not validate credentials"
Solution: Use refresh endpoint to get new access token
```

### Insufficient Permissions
```
Error: "Access denied. Admin role required."
Solution: User doesn't have required role. Use admin account or ask admin to upgrade role.
```

### User Not Found
```
Error: "User not found"
Solution: Use valid user ID or verify user exists in database
```

## Performance Considerations

- Database indexes on email and user_id for faster lookups
- Role and permission caching at application level
- JWT tokens are stateless - no database lookup needed for validation
- Connection pooling for database efficiency

## Future Enhancements

1. **Multi-factor Authentication (MFA)**
   - SMS OTP verification
   - Email verification
   - TOTP support

2. **Audit Logging**
   - Track all permission changes
   - Log authentication attempts
   - Monitor privileged actions

3. **API Rate Limiting**
   - Prevent brute force attacks
   - Limit API calls per user

4. **Advanced Permissions**
   - Resource-level permissions
   - Time-based access control
   - Delegation of authority

5. **OAuth 2.0 Integration**
   - Google/GitHub login
   - Social sign-in options

## Development Notes

- All passwords are hashed using bcrypt
- JWT uses HS256 algorithm
- Database uses SQLAlchemy ORM
- FastAPI dependencies pattern for middleware
- Type hints throughout for better IDE support

## Support & Questions

For issues or questions regarding authentication and RBAC:
1. Check server logs for detailed error messages
2. Verify user exists in database
3. Confirm role assignments
4. Check token expiration status
5. Review .env configuration

---

**Last Updated**: February 2024
**Version**: 1.0.0
