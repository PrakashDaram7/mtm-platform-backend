
from sqlalchemy import inspect
from app.core.database import engine


def check_database_connection():
    """
    Check if the database connection is active and working.
    
    Returns:
        dict: A dictionary with 'status' (success/failure) and 'message' keys.
    """
    try:
        # Try to get the database inspector
        inspector = inspect(engine)
        
        # If we can get table names, connection is valid
        tables = inspector.get_table_names()
        return {
            "status": "success",
            "message": f"Database connection successful! Found {len(tables)} tables."
        }
    except Exception as e:
        return {
            "status": "failure",
            "message": f"Database connection failed: {str(e)}"
        }
