"""Database configuration and session management.

TODO: Add SQLAlchemy engine setup, session factory, and database initialization.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

if not MYSQL_USER or not MYSQL_PASSWORD or not MYSQL_DATABASE:
    raise ValueError("Missing MySQL environment variables in .env file")

encoded_password = quote_plus(MYSQL_PASSWORD)

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{encoded_password}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)

# DATABASE_URL = "mysql+pymysql://root:Mysql%40123@localhost:3306/mtm_db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()




