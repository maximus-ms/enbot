"""Base model configuration."""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from enbot.config import settings

# Create SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""
    created_at = DateTime(default=datetime.utcnow)
    updated_at = DateTime(default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db() -> Any:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database."""
    Base.metadata.create_all(bind=engine) 