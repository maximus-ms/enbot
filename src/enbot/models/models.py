"""Database models for the bot."""
from datetime import datetime, UTC
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import relationship

from enbot.models.base import Base


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps."""

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class User(Base, TimestampMixin):
    """User model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=True)
    is_admin = Column(Boolean, default=False)
    native_language = Column(String, nullable=False)
    target_language = Column(String, nullable=False)
    daily_goal_minutes = Column(Integer, default=10)
    daily_goal_words = Column(Integer, default=5)
    day_start_hour = Column(Integer, default=0)
    notification_hour = Column(Integer, default=0)
    last_notification_time = Column(DateTime(timezone=True), nullable=True)
    notifications_enabled = Column(Boolean, default=True)

    # Relationships
    words = relationship("UserWord", back_populates="user")
    learning_cycles = relationship("LearningCycle", back_populates="user")
    logs = relationship("UserLog", back_populates="user")


class Word(Base, TimestampMixin):
    """Word model."""

    __tablename__ = "words"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    translation = Column(String, nullable=False)
    transcription = Column(String)
    pronunciation_file = Column(String)
    image_file = Column(String)
    language_pair = Column(String, nullable=False)  # e.g., "en-uk"

    # Relationships
    users = relationship("UserWord", back_populates="word")
    examples = relationship("Example", back_populates="word")


class UserWord(Base, TimestampMixin):
    """User-word association model."""

    __tablename__ = "user_words"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    priority = Column(Integer, default=0)  # 0-10, 11 for repetition
    is_learned = Column(Boolean, default=False)
    last_reviewed = Column(DateTime(timezone=True))
    next_review = Column(DateTime(timezone=True))
    review_stage = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="words")
    word = relationship("Word", back_populates="users")
    cycle_words = relationship("CycleWord", back_populates="user_word")


class Example(Base, TimestampMixin):
    """Example sentence model."""

    __tablename__ = "examples"

    id = Column(Integer, primary_key=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    sentence = Column(String, nullable=False)
    translation = Column(String, nullable=False)
    is_good = Column(Boolean, default=True)

    # Relationships
    word = relationship("Word", back_populates="examples")


class LearningCycle(Base, TimestampMixin):
    """Learning cycle model."""

    __tablename__ = "learning_cycles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    is_completed = Column(Boolean, default=False)
    words_learned = Column(Integer, default=0)
    time_spent = Column(Float, default=0.0)  # in minutes

    # Relationships
    user = relationship("User", back_populates="learning_cycles")
    cycle_words = relationship("CycleWord", back_populates="cycle")


class CycleWord(Base, TimestampMixin):
    """Cycle-word association model."""

    __tablename__ = "cycle_words"

    id = Column(Integer, primary_key=True)
    cycle_id = Column(Integer, ForeignKey("learning_cycles.id"), nullable=False)
    user_word_id = Column(Integer, ForeignKey("user_words.id"), nullable=False)
    is_learned = Column(Boolean, default=False)
    time_spent = Column(Float, default=0.0)  # in minutes

    # Relationships
    cycle = relationship("LearningCycle", back_populates="cycle_words")
    user_word = relationship("UserWord", back_populates="cycle_words")


class UserLog(Base, TimestampMixin):
    """User activity log model."""

    __tablename__ = "user_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String, nullable=False)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR
    category = Column(String, nullable=False)  # e.g., "learning", "settings"

    # Relationships
    user = relationship("User", back_populates="logs")
