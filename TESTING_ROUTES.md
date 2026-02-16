# Testing Role-Based Routes - Examples

This document provides curl command examples for testing the role-based protected routes.

## Authentication Flow

### 1. Register a New User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d {
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "password": "SecurePassword123!"
  }
```

### 2. Login User
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d {
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

## Public Endpoints (No Authentication Required)

### Get Health Status
```bash
curl http://localhost:8000/health
```

### List Events
```bash
curl http://localhost:8000/api/events
```

### Get Event Details
```bash
curl http://localhost:8000/api/events/event-123
```

### List Members
```bash
curl http://localhost:8000/api/members
```

### Get Member Profile
```bash
curl http://localhost:8000/api/members/member-123
```

## Authenticated User Routes

**Use the access token from login response:**

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Get Current User Profile
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/members/me/profile
```

### Create Event
```bash
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "title": "Tech Meetup",
    "description": "A tech meetup",
    "date": "2026-03-01",
    "location": "New York"
  }
```

### Register for Event
```bash
curl -X POST http://localhost:8000/api/events/event-123/register \
  -H "Authorization: Bearer $TOKEN"
```

### Get My Notifications
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/notifications/my-notifications
```

### Create Payment
```bash
curl -X POST http://localhost:8000/api/payments/create-payment \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "amount": 99.99,
    "description": "Event ticket"
  }
```

### Update Profile
```bash
curl -X PUT http://localhost:8000/api/members/me/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "full_name": "John Updated",
    "phone": "+1987654321"
  }
```

### Update Notification Preferences
```bash
curl -X PUT http://localhost:8000/api/notifications/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "email_notifications": true,
    "push_notifications": false,
    "sms_notifications": true
  }
```

## Admin-Only Routes

### List All Users
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/users
```

### Get User Details
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/users/user-123
```

### Update User Role
```bash
curl -X PUT http://localhost:8000/api/admin/users/user-123/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "role_name": "moderator"
  }
```

### Deactivate User
```bash
curl -X POST http://localhost:8000/api/admin/users/user-123/deactivate \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "reason": "Violation of terms"
  }
```

### Activate User
```bash
curl -X POST http://localhost:8000/api/admin/users/user-123/activate \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Delete User
```bash
curl -X DELETE http://localhost:8000/api/admin/users/user-123 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### List All Roles
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/roles
```

### Get Role Details
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/roles/admin
```

### Get System Statistics
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/stats/summary
```

### Get User Activity Statistics
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/stats/users/activity
```

### List All Payments
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/payments/admin/all-payments
```

### Get Payment Details
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/payments/admin/payment/payment-123
```

### Approve Payment
```bash
curl -X POST http://localhost:8000/api/payments/admin/payment/payment-123/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Reject Payment
```bash
curl -X POST http://localhost:8000/api/payments/admin/payment/payment-123/reject \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "reason": "Invalid payment method"
  }
```

### Process Refund
```bash
curl -X POST http://localhost:8000/api/payments/admin/payment/payment-123/refund \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "reason": "Customer request",
    "amount": 50.00
  }
```

### List Pending Payments
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/payments/admin/pending-approvals
```

### List All Notifications
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/notifications/admin/all-notifications
```

### Send Notification to User
```bash
curl -X POST http://localhost:8000/api/notifications/admin/send-notification \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "recipient_user_id": "user-123",
    "title": "Important Update",
    "message": "Your account has been updated",
    "notification_type": "admin_message"
  }
```

### Broadcast Notification
```bash
curl -X POST http://localhost:8000/api/notifications/admin/broadcast-notification \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "title": "System Maintenance",
    "message": "System will be down for maintenance tonight",
    "notification_type": "announcement",
    "target_role": null
  }
```

### Get Notification Statistics
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/notifications/admin/stats/summary
```

### List All Members (Admin View)
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/members/admin/all-members
```

### Get Member Profile (Admin View)
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/members/admin/user-123/profile
```

### Update Member Profile (Admin)
```bash
curl -X PUT http://localhost:8000/api/members/admin/user-123/profile \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "full_name": "Jane Doe",
    "phone": "+1111111111"
  }
```

### Verify Member Email (Admin)
```bash
curl -X POST http://localhost:8000/api/members/admin/user-123/verify-email \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Approve Event (Admin)
```bash
curl -X POST http://localhost:8000/api/events/event-123/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Reject Event (Admin)
```bash
curl -X POST http://localhost:8000/api/events/event-123/reject \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "reason": "Inappropriate content"
  }
```

## Authorization Failures

### Missing Token (Should Return 401)
```bash
curl http://localhost:8000/api/admin/users
# Response: 401 Could not validate credentials
```

### Invalid Token Format
```bash
curl -H "Authorization: InvalidToken" \
  http://localhost:8000/api/admin/users
# Response: 401 Could not validate credentials
```

### User Token to Admin Endpoint (Should Return 403)
```bash
curl -H "Authorization: Bearer $USER_TOKEN" \
  http://localhost:8000/api/admin/users
# Response: 403 Admin access required
```

### Expired Token
```bash
curl -H "Authorization: Bearer $EXPIRED_TOKEN" \
  http://localhost:8000/api/admin/users
# Response: 401 Could not validate credentials
```

## Pagination Examples

### With Skip and Limit
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8000/api/admin/users?skip=0&limit=5"
```

### With Filters
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8000/api/admin/users?role_filter=admin&is_active=true"
```

## Setting Up Tokens for Testing

### Using Bash Variables
```bash
# Store admin token
export ADMIN_TOKEN="your_admin_token_here"

# Store user token
export USER_TOKEN="your_user_token_here"

# Use in commands
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/admin/users
```

### Using PowerShell
```powershell
# Store admin token
$adminToken = "your_admin_token_here"

# Store user token
$userToken = "your_user_token_here"

# Use in commands
curl -H "Authorization: Bearer $adminToken" http://localhost:8000/api/admin/users
```

## Common Issues and Solutions

### 401 Unauthorized
**Problem**: Token is missing or invalid
**Solution**: 
- Check token is included in Authorization header
- Verify token hasn't expired
- Check token format is "Bearer {token}"

### 403 Forbidden
**Problem**: User doesn't have required role
**Solution**:
- Verify user has correct role assigned
- Check role is active in database
- Verify user account is active

### 404 Not Found
**Problem**: Resource doesn't exist
**Solution**:
- Check ID is correct
- Verify resource exists in database
- Check user has permission to view resource

### 422 Unprocessable Entity
**Problem**: Request validation failed
**Solution**:
- Check request body matches schema
- Verify required fields are included
- Check data types are correct
