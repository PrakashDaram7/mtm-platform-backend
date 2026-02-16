# Quick Start Guide - Authentication & RBAC System

## 5-Minute Setup

### Step 1: Start MySQL
Ensure MySQL is running with credentials from `.env`:
- User: `root`
- Password: `Mysql@143`
- Database: `mtm_db`

### Step 2: Run Seed Script
```bash
python seed.py
```
Creates default roles and 5 sample users.

### Step 3: Start Server
```bash
python main.py
```
Server runs at: `http://localhost:8000`

### Step 4: Open API Docs
Navigate to: `http://localhost:8000/docs`

---

## Quick Testing

### Test 1: Login as Admin
**Endpoint**: `POST /api/auth/login`
```json
Body: {
  "email": "admin@mtm.com",
  "password": "admin123"
}
```

**Response**: Get `access_token` and `refresh_token`

### Test 2: Access Admin Panel
**Endpoint**: `GET /api/test/admin/dashboard`

Add to headers:
```
Authorization: Bearer {access_token}
```

**Response**: Admin dashboard data with statistics

### Test 3: List Users (Admin Only)
**Endpoint**: `GET /api/auth/users`

Add to headers:
```
Authorization: Bearer {admin_token}
```

### Test 4: Try User Dashboard
**Use**: `user@mtm.com / user123` token

**Endpoint**: `GET /api/test/user/dashboard`

Should succeed (authenticated user)

### Test 5: Try Admin Endpoint as User
**Use**: `user@mtm.com / user123` token

**Endpoint**: `GET /api/test/admin/dashboard`

**Expected**: 403 Forbidden (insufficient permissions)

---

## Sample User Accounts

| Role | Email | Password | Permissions |
|------|-------|----------|-------------|
| **Admin** | admin@mtm.com | admin123 | Full system access |
| **Moderator** | moderator@mtm.com | moderator123 | User moderation, content management |
| **Organizer** | organizer@mtm.com | organizer123 | Event creation and management |
| **Member** | member@mtm.com | member123 | Standard member access |
| **User** | user@mtm.com | user123 | Basic user access |

---

## Key API Endpoints

### Authentication
- `POST /api/auth/register` - Create new user
- `POST /api/auth/login` - Login (get tokens)
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/change-password` - Update password

### User Management (Admin)
- `GET /api/auth/users` - List all users
- `PUT /api/auth/users/{user_id}/role` - Change user role
- `POST /api/auth/users/{user_id}/disable` - Disable user
- `POST /api/auth/users/{user_id}/enable` - Enable user

### Role-Based Dashboards
- `GET /api/test/user/dashboard` - User dashboard
- `GET /api/test/moderator/dashboard` - Moderator panel
- `GET /api/test/admin/dashboard` - Admin panel

### Testing RBAC
- `GET /api/test/user/permissions` - View your permissions
- `GET /api/test/test/role-check/{user_id}` - Check user role
- `GET /api/test/test/permission-check/{resource}/{action}` - Test permission

---

## Using Swagger UI

1. Go to `http://localhost:8000/docs`
2. Find **"Authorize"** button at top right
3. Select **"HTTPBearer"**
4. Paste your access token
5. Click **"Authorize"**
6. Now test any endpoint directly

---

## Complete Authentication Flow

```
1. User Register or Login
   └─> Receive: access_token + refresh_token

2. Include in Every Request
   └─> Header: Authorization: Bearer {access_token}

3. Token Expires (30 min)
   └─> Use refresh_token to get new access_token
   └─> POST /api/auth/refresh

4. Access Protected Routes
   └─> System verifies token
   └─> Checks user role/permissions
   └─> Grants or denies access
```

---

## Role-Based Access Examples

### Admin Can:
✅ View all users
✅ Change user roles
✅ Disable/enable accounts
✅ View system statistics
✅ Access admin dashboard

### Moderator Can:
✅ View user list
✅ Flag users for review
✅ Moderate content
✅ View moderator panel

### User Can:
✅ View own profile
✅ Update own profile
✅ View personal dashboard
❌ Cannot access admin panel
❌ Cannot view other users

---

## Common Issues & Solutions

### Issue: "Could not validate credentials"
**Cause**: Invalid or expired token
**Solution**: 
1. Re-login to get new token
2. Or use refresh endpoint to get new access token

### Issue: "Access denied. Admin role required"
**Cause**: User doesn't have admin role
**Solution**: 
1. Use admin account
2. Or ask admin to promote your account

### Issue: Database connection failed
**Cause**: MySQL not running or wrong credentials
**Solution**:
1. Start MySQL service
2. Check `.env` file credentials
3. Verify database exists

### Issue: Token expired
**Cause**: Access token expires after 30 minutes
**Solution**: 
```bash
POST /api/auth/refresh
Body: {"refresh_token": "your_refresh_token"}
```

---

## Testing Tool Recommendations

### Command Line (cURL)
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Postman
1. Create collection
2. Set "Authorization" tab to "Bearer Token"
3. Paste access token
4. Save requests for reuse

### VS Code REST Client
Create `test.http`:
```http
### Login
POST http://localhost:8000/api/auth/login
Content-Type: application/json

{
  "email": "admin@mtm.com",
  "password": "admin123"
}

### Get Profile
GET http://localhost:8000/api/auth/me
Authorization: Bearer {access_token}
```

### Swagger UI (Easiest)
1. Open `http://localhost:8000/docs`
2. Click "Authorize" button
3. Paste token
4. Test directly

---

## Performance Tips

1. **Minimize Token Requests**: Reuse tokens until expiry
2. **Use Connection Pooling**: Database maintains persistent connections
3. **Cache Roles**: Reduce DB lookups for role checks
4. **Index Lookups**: Email and user_id have database indexes
5. **Stateless Design**: JWT tokens don't require DB validation

---

## Next Steps

1. ✅ System is running
2. ✅ Seed data is loaded
3. ✅ Test endpoints from Swagger UI
4. ➡️ Integrate with your frontend
5. ➡️ Add custom business logic routes
6. ➡️ Customize permissions as needed

---

## Need Help?

Check the full documentation in `AUTH_RBAC_GUIDE.md` for:
- Complete API reference
- Detailed role descriptions
- Advanced permission management
- Troubleshooting guide
- Security best practices

---

**Happy Coding!** 🚀
