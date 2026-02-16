# Role-Based Access Control (RBAC) Implementation Guide

This document explains how role-based access control is implemented across the MTM Platform Backend routes.

## Overview

The backend uses a hierarchical RBAC system with the following components:

- **Roles**: Define user roles (admin, moderator, user)
- **Permissions**: Define what actions users can perform on resources
- **RBAC Middleware**: Provides dependency injection for route protection
- **Protected Routes**: Routes that require specific roles or permissions

## System Architecture

### Role Model
```python
- role_id: Unique identifier
- role_name: Role name (e.g., 'admin', 'user', 'moderator')
- description: Role description
- permissions: List of associated permissions
- users: List of users assigned to this role
```

### Permission Model
```python
- permission_id: Unique identifier
- permission_name: Permission name
- resource: Resource name (e.g., 'users', 'events', 'payments')
- action: Action name (e.g., 'create', 'read', 'update', 'delete')
- role_id: Associated role
```

### User Model
```python
- id: Unique identifier
- email: User email
- role_id: Associated role (foreign key to Role)
- role: Relationship to Role model
```

## RBAC Middleware Dependencies

The `app/core/rbac_middleware.py` provides these key dependencies:

### 1. `require_authenticated`
Requires user to be authenticated and active.

```python
@router.get("/protected-endpoint")
async def protected_endpoint(
    current_user: User = Depends(require_authenticated)
) -> dict:
    return {"message": f"Welcome {current_user.full_name}"}
```

### 2. `require_admin`
Requires user to have admin role.

```python
@router.get("/admin-only")
async def admin_endpoint(
    current_user: User = Depends(require_admin)
) -> dict:
    return {"message": "Admin section"}
```

### 3. `require_moderator`
Requires user to have moderator role.

```python
@router.get("/moderator-only")
async def moderator_endpoint(
    current_user: User = Depends(require_moderator)
) -> dict:
    return {"message": "Moderator section"}
```

### 4. `require_user`
Requires user to have user role.

```python
@router.get("/user-section")
async def user_endpoint(
    current_user: User = Depends(require_user)
) -> dict:
    return {"message": "User section"}
```

### 5. `RBACMiddleware.require_role`
Requires user to have a specific role (dynamic).

```python
async def admin_dashboard(
    current_user: User = RBACMiddleware.require_role("admin")
) -> dict:
    return {"message": "Admin dashboard"}
```

### 6. `RBACMiddleware.require_any_role`
Requires user to have any of multiple roles.

```python
async def moderator_or_admin(
    current_user: User = RBACMiddleware.require_any_role(["admin", "moderator"])
) -> dict:
    return {"message": "Moderator or Admin section"}
```

### 7. `RBACMiddleware.require_permission`
Requires user to have specific resource permission.

```python
async def create_event(
    event_data: dict = Body(...),
    current_user: User = RBACMiddleware.require_permission("events", "create")
) -> dict:
    return {"message": "Event created"}
```

## Protected Routes Overview

### Authentication Routes (`/api/auth`)
- **POST** `/register` - Public endpoint, creates new user
- **POST** `/login` - Public endpoint, returns JWT tokens
- **GET** `/me` - Requires authentication
- **GET** `/admin-only` - Requires admin role
- **GET** `/moderator-only` - Requires moderator role
- **GET** `/protected` - Requires authentication
- **GET** `/users` - Requires admin role
- **PUT** `/users/{user_id}/role` - Requires admin role
- **POST** `/users/{user_id}/disable` - Requires admin role

### Admin Routes (`/api/admin`)
**All endpoints require admin role**

#### User Management
- **GET** `/users` - List all users
- **GET** `/users/{user_id}` - Get user details
- **PUT** `/users/{user_id}/role` - Update user role
- **POST** `/users/{user_id}/activate` - Activate user
- **POST** `/users/{user_id}/deactivate` - Deactivate user
- **DELETE** `/users/{user_id}` - Delete user permanently

#### Role Management
- **GET** `/roles` - List all roles
- **GET** `/roles/{role_name}` - Get role details

#### Statistics
- **GET** `/stats/summary` - System statistics
- **GET** `/stats/users/activity` - User activity stats

### Events Routes (`/api/events`)

#### Public Endpoints
- **GET** `` - List events (public)
- **GET** `/{event_id}` - Get event details (public)

#### Authenticated User Endpoints
- **POST** `` - Create event (requires authentication)
- **PUT** `/{event_id}` - Update event (requires authentication + authorization)
- **DELETE** `/{event_id}` - Delete event (requires authentication + authorization)
- **POST** `/{event_id}/register` - Register for event (requires authentication)
- **DELETE** `/{event_id}/register` - Unregister from event (requires authentication)
- **GET** `/{event_id}/attendees` - Get event attendees (requires authentication)

#### Admin Endpoints
- **GET** `/admin/pending-approval` - Get pending events (admin only)
- **POST** `/{event_id}/approve` - Approve event (admin only)
- **POST** `/{event_id}/reject` - Reject event (admin only)

### Members Routes (`/api/members`)

#### Public Endpoints
- **GET** `` - List public member profiles
- **GET** `/{member_id}` - Get public member profile

#### Authenticated User Endpoints
- **GET** `/me/profile` - Get current user's profile (requires authentication)
- **PUT** `/me/profile` - Update current user's profile (requires authentication)
- **GET** `/me/activity` - Get user activity (requires authentication)
- **GET** `/me/events` - Get user's events (requires authentication)
- **POST** `/me/change-password` - Change password (requires authentication)
- **POST** `/me/update-email` - Update email (requires authentication)

#### Admin Endpoints
- **GET** `/admin/all-members` - List all members (admin only)
- **GET** `/admin/{member_id}/profile` - Get member profile (admin only)
- **PUT** `/admin/{member_id}/profile` - Update member profile (admin only)
- **POST** `/admin/{member_id}/verify-email` - Verify email (admin only)
- **GET** `/admin/pending-verification` - Pending verifications (admin only)
- **POST** `/admin/{member_id}/send-verification-email` - Send email (admin only)

### Payments Routes (`/api/payments`)

#### Authenticated User Endpoints
- **POST** `/create-payment` - Create payment (requires authentication)
- **GET** `/my-payments` - Get user's payments (requires authentication)
- **GET** `/payment/{payment_id}` - Get payment details (requires authentication)
- **POST** `/payment/{payment_id}/cancel` - Cancel payment (requires authentication)
- **POST** `/payment/{payment_id}/refund-request` - Request refund (requires authentication)
- **GET** `/invoice/{payment_id}` - Download invoice (requires authentication)

#### Admin Endpoints
- **GET** `/admin/all-payments` - List all payments (admin only)
- **GET** `/admin/payment/{payment_id}` - Get payment details (admin only)
- **POST** `/admin/payment/{payment_id}/approve` - Approve payment (admin only)
- **POST** `/admin/payment/{payment_id}/reject` - Reject payment (admin only)
- **POST** `/admin/payment/{payment_id}/refund` - Process refund (admin only)
- **GET** `/admin/pending-approvals` - Pending payments (admin only)
- **GET** `/admin/pending-refunds` - Pending refunds (admin only)
- **GET** `/admin/stats/summary` - Payment stats (admin only)
- **GET** `/admin/stats/daily` - Daily stats (admin only)

### Notifications Routes (`/api/notifications`)

#### Authenticated User Endpoints
- **GET** `/my-notifications` - Get user's notifications (requires authentication)
- **GET** `/notification/{notification_id}` - Get notification (requires authentication)
- **POST** `/notification/{notification_id}/mark-as-read` - Mark as read (requires authentication)
- **POST** `/mark-all-as-read` - Mark all as read (requires authentication)
- **POST** `/notification/{notification_id}/delete` - Delete notification (requires authentication)
- **POST** `/delete-all` - Delete all notifications (requires authentication)
- **GET** `/unread-count` - Get unread count (requires authentication)
- **GET** `/preferences` - Get preferences (requires authentication)
- **PUT** `/preferences` - Update preferences (requires authentication)

#### Admin Endpoints
- **GET** `/admin/all-notifications` - List all notifications (admin only)
- **POST** `/admin/send-notification` - Send notification (admin only)
- **POST** `/admin/broadcast-notification` - Broadcast notification (admin only)
- **GET** `/admin/stats/summary` - Notification stats (admin only)
- **POST** `/admin/notification/{notification_id}/resend` - Resend (admin only)
- **DELETE** `/admin/notification/{notification_id}` - Delete (admin only)

## Error Responses

### Unauthorized (401)
Returns when user is not authenticated or token is invalid:
```json
{
    "detail": "Could not validate credentials"
}
```

### Forbidden (403)
Returns when user doesn't have required role or permission:
```json
{
    "detail": "Admin access required"
}
```

### Not Found (404)
Returns when requested resource doesn't exist:
```json
{
    "detail": "User not found"
}
```

### Bad Request (400)
Returns when request data is invalid:
```json
{
    "detail": "Invalid request data"
}
```

## How Authorization Works

1. **User Logs In**: User provides email and password
2. **Token Generation**: Backend creates JWT token containing user_id, email, and roles
3. **Request with Token**: Client includes token in Authorization header
4. **Token Validation**: Backend validates token signature and expiration
5. **Role Check**: If route requires role, backend checks user's role
6. **Permission Check**: If route requires permission, backend checks user's permissions
7. **Request Processing**: If authorized, request is processed and response returned

## Token Format

JWT tokens include:
```json
{
    "user_id": "uuid",
    "email": "user@example.com",
    "roles": ["user"],
    "exp": 1234567890,
    "iat": 1234567890
}
```

## Adding Role Protection to New Routes

### Method 1: Require Specific Role
```python
@router.get("/admin-endpoint")
async def admin_endpoint(
    current_user: User = Depends(require_admin)
) -> dict:
    # Only admins can access this
    return {"message": "Admin only"}
```

### Method 2: Require Any of Multiple Roles
```python
@router.get("/moderator-or-admin")
async def moderator_endpoint(
    current_user: User = RBACMiddleware.require_any_role(["admin", "moderator"])
) -> dict:
    # Admins or moderators can access
    return {"message": "Moderator or admin only"}
```

### Method 3: Check Authorization in Handler
```python
@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    event_data: dict,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    # Fetch event and check if current user is creator
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.creator_id != current_user.id and not user_has_role(current_user, "admin"):
        raise HTTPException(
            status_code=403,
            detail="You can only update your own events"
        )
    
    # Update event
    return {"message": "Event updated"}
```

### Method 4: Middleware-Level Protection
```python
@router.get("/admin-endpoint", dependencies=[Depends(require_admin)])
async def admin_endpoint(
    db: Session = Depends(get_db)
) -> dict:
    # Protection happens before handler is called
    return {"message": "Admin only"}
```

## Best Practices

1. **Use Specific Dependencies**: Be as specific as possible (require_admin vs require_authenticated)
2. **Validate Ownership**: For resource endpoints, always verify user owns the resource
3. **Log Access Attempts**: Track failed authorization attempts
4. **Keep Tokens Secure**: Never log or expose tokens
5. **Regular Role Audits**: Periodically review role assignments
6. **Principle of Least Privilege**: Assign minimal required permissions
7. **Separate Concerns**: Keep authentication separate from business logic
8. **Test Authorization**: Always test that unauthorized users are rejected

## Testing Protected Routes

### With Valid Admin Token
```bash
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/api/admin/users
```

### Without Token (Should Fail)
```bash
curl http://localhost:8000/api/admin/users
# Returns 401 Unauthorized
```

### With User Token to Admin Endpoint (Should Fail)
```bash
curl -H "Authorization: Bearer <user_token>" \
  http://localhost:8000/api/admin/users
# Returns 403 Forbidden
```

## Security Considerations

1. **Token Expiration**: Access tokens expire after 30 minutes
2. **Refresh Tokens**: Refresh tokens last 7 days
3. **Password Hashing**: Passwords hashed with bcrypt
4. **HTTPS**: Always use HTTPS in production
5. **CORS**: Configure CORS appropriately for your frontend
6. **Rate Limiting**: Consider implementing rate limiting for authentication endpoints
7. **Audit Logging**: Log all admin actions for security auditing

## Troubleshooting

### User Gets 403 Forbidden on Role-Protected Route
- Verify user has the required role assigned
- Check that role is active (is_active=True)
- Ensure user account is active (is_active=True)

### JWT Token Invalid
- Check token has not expired
- Verify token was not modified
- Ensure SECRET_KEY matches between token generation and validation

### Role Not Found
- Verify role exists in database
- Check role name spelling matches exactly
- Ensure role is active

## Migration Guide

If migrating from a non-RBAC system:

1. Create role records in database
2. Create permission records
3. Assign roles to existing users via UPDATE query
4. Update routes to include proper dependencies
5. Test all protected endpoints
6. Deploy with feature flag if needed
7. Monitor for authorization errors
