"""FastAPI application entry point with RBAC support."""
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.utils.helpers import check_database_connection
from app.modules.auth.routes import router as auth_router

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
    print(f"\n{'='*60}")
    print(f"🚀 MTM Platform Backend - Startup Check")
    print(f"{'='*60}")
    print(f"Database Status: {db_check['status'].upper()}")
    print(f"Message: {db_check['message']}")
    print(f"{'='*60}\n")
    
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

# Include test router for RBAC demonstrations
try:
    from app.modules.test.routes import router as test_router
    app.include_router(test_router, tags=["testing"])
except Exception as e:
    print(f"Warning: Could not import test routes: {e}")


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 Starting MTM Platform Backend Server")
    print("="*60)
    print("Debug: False")
    print("Host: 0.0.0.0")
    print("Port: 8000")
    print("Docs: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
