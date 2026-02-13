"""FastAPI application entry point."""
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.utils.helpers import check_database_connection

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="MTM Platform Backend",
    description="Backend API for MTM Digital Platform",
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
    """Check database connection on server startup."""
    db_check = check_database_connection()
    print(f"\n{'='*50}")
    print(f"Server Startup Check:")
    print(f"Status: {db_check['status'].upper()}")
    print(f"Message: {db_check['message']}")
    print(f"{'='*50}\n")
    
    if db_check['status'] == "failure":
        print("⚠️  Warning: Database connection failed. Server is running but database features may not work.")


@app.on_event("shutdown")
async def shutdown_event():
    """Log server shutdown."""
    print("\n✓ Server shutdown successfully.\n")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to MTM Platform Backend",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_check = check_database_connection()
    return {
        "status": "healthy",
        "database": db_check
    }


# Include module routes
from app.modules.auth.routes import router as auth_router
# from app.modules.admin.routes import router as admin_router
# from app.modules.members.routes import router as members_router
# from app.modules.events.routes import router as events_router
# from app.modules.payments.routes import router as payments_router
# from app.modules.notifications.routes import router as notifications_router

app.include_router(auth_router, prefix="/api", tags=["auth"])
# app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
# app.include_router(members_router, prefix="/api/members", tags=["members"])
# app.include_router(events_router, prefix="/api/events", tags=["events"])
# app.include_router(payments_router, prefix="/api/payments", tags=["payments"])
# app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])


if __name__ == "__main__":
    import uvicorn
    
    print("\n🚀 Starting MTM Platform Backend Server...\n")
    uvicorn.run(
        "main:app",
        host="192.168.0.185",
        port=8000,
        reload=True  # Enable auto-reload on code changes
    )
