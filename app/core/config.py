"""Application configuration.

Loads environment variables for database, JWT, and other settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# MySQL Configuration
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-12345678")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# OTP Configuration
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "2"))

# Email Configuration (FastAPI SMTP - using smtplib)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "daramprakashkumar587@gmail.com").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "hyos fhti mehi fkgq").strip()
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "noreply@mtmplatform.com")

# Server Configuration
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
