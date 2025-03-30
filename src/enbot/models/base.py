"""Base model configuration."""
from datetime import UTC, datetime
from typing import Any, Generator

from sqlalchemy import Column, DateTime, create_engine, func, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.engine import Engine

from enbot.config import settings

# Create SQLAlchemy engine
engine = create_engine(settings.database.url)

# Configure SQLite to handle timezone-aware datetimes
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragma for timezone-aware datetimes."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA timezone=UTC")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base class
Base = declarative_base()


class TimestampMixin:
    """Mixin to add timestamp columns to models."""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database."""
    Base.metadata.create_all(bind=engine)  # Create tables if they don't exist 