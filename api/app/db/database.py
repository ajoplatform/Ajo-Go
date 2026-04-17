from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os


def get_database_url():
    """Get database URL from environment or use SQLite for local dev."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    # Default to SQLite for local development
    return os.getenv("LOCAL_DATABASE_URL", "sqlite:///./db.sqlite3")


DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
