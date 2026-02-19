"""FastAPI application entry point with RBAC support."""
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.utils.helpers import check_database_connection
from app.modules.auth.routes import router as auth_router

# Import ALL models so SQLAlchemy knows about them and creates tables
from app.modules.auth.models import User, Role, Permission, OTP
from app.modules.events.models import Event, EventRegistration
from app.modules.members.models import MembershipPlan, MemberSubscription
from app.modules.notifications.models import Notification
from app.modules.payments.models import Payment

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="MTM Platform Backend",
    description="Backend API for MTM Digital Platform with RBAC",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    db_check = check_database_connection()

    
    if db_check['status'] == "failure":
        print("⚠️  Warning: Database connection failed. Server is running but database features may not work.")
    else:
        print("✓ RBAC system loaded and ready")
        print("✓ Authentication system initialized")
        print("✓ Role-Based Access Control (RBAC) enabled\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Log server shutdown."""
    print("\n✓ Server shutdown successfully.\n")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to MTM Platform Backend",
        "status": "running",
        "features": ["Authentication", "RBAC", "OTP Verification"],
        "api_docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_check = check_database_connection()
    return {
        "status": "healthy",
        "database": db_check,
        "rbac_enabled": True,
        "authentication_enabled": True
    }


# Include routers
app.include_router(auth_router, prefix="/api", tags=["auth"])

# Include admin router
try:
    from app.modules.admin.routes import router as admin_router
    app.include_router(admin_router, prefix="/api", tags=["admin"])
except Exception as e:
    print(f"Warning: Could not import admin routes: {e}")

# Include moderator router
try:
    from app.modules.moderator.routes import router as moderator_router
    app.include_router(moderator_router, prefix="/api", tags=["moderator"])
except Exception as e:
    print(f"Warning: Could not import moderator routes: {e}")

# Include organizer router
try:
    from app.modules.organizer.routes import router as organizer_router
    app.include_router(organizer_router, prefix="/api", tags=["organizer"])
except Exception as e:
    print(f"Warning: Could not import organizer routes: {e}")

# Include members router
try:
    from app.modules.members.routes import router as members_router
    app.include_router(members_router, prefix="/api", tags=["members"])
except Exception as e:
    print(f"Warning: Could not import members routes: {e}")

# Include events router
try:
    from app.modules.events.routes import router as events_router
    app.include_router(events_router, prefix="/api", tags=["events"])
except Exception as e:
    print(f"Warning: Could not import events routes: {e}")


if __name__ == "__main__":
    import uvicorn
    

    uvicorn.run(
        "main:app",
        host="192.168.0.231",
        port=8000,
        reload=True
    )
