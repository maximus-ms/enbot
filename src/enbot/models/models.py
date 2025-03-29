"""Core database models."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from enbot.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    is_admin = Column(Boolean, default=False)
    native_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    daily_goal_minutes = Column(Integer, default=10)
    daily_goal_words = Column(Integer, default=5)
    day_start_hour = Column(Integer, default=3)

    # Relationships
    words = relationship("UserWord", back_populates="user")
    learning_cycles = relationship("LearningCycle", back_populates="user")
    logs = relationship("UserLog", back_populates="user")


class Word(Base, TimestampMixin):
    """Word model."""
    __tablename__ = "words"

    id = Column(Integer, primary_key=True)
    text = Column(String(255), nullable=False)
    translation = Column(String(255), nullable=False)
    transcription = Column(String(255))
    pronunciation_file = Column(String(255))
    image_file = Column(String(255))
    language_pair = Column(String(20), nullable=False)  # e.g., "en-uk"

    # Relationships
    user_words = relationship("UserWord", back_populates="word")
    examples = relationship("Example", back_populates="word")


class Example(Base, TimestampMixin):
    """Example sentence model."""
    __tablename__ = "examples"

    id = Column(Integer, primary_key=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    sentence = Column(Text, nullable=False)
    translation = Column(Text, nullable=False)
    is_good = Column(Boolean, default=True)

    # Relationships
    word = relationship("Word", back_populates="examples")


class UserWord(Base, TimestampMixin):
    """User-specific word data."""
    __tablename__ = "user_words"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    priority = Column(Integer, default=0)
    is_learned = Column(Boolean, default=False)
    last_reviewed = Column(DateTime)
    next_review = Column(DateTime)
    review_stage = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="words")
    word = relationship("Word", back_populates="user_words")


class LearningCycle(Base, TimestampMixin):
    """Learning cycle model."""
    __tablename__ = "learning_cycles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    words_learned = Column(Integer, default=0)
    time_spent = Column(Float, default=0.0)  # in minutes

    # Relationships
    user = relationship("User", back_populates="learning_cycles")
    cycle_words = relationship("CycleWord", back_populates="cycle")


class CycleWord(Base, TimestampMixin):
    """Words in a learning cycle."""
    __tablename__ = "cycle_words"

    id = Column(Integer, primary_key=True)
    cycle_id = Column(Integer, ForeignKey("learning_cycles.id"), nullable=False)
    user_word_id = Column(Integer, ForeignKey("user_words.id"), nullable=False)
    is_learned = Column(Boolean, default=False)
    time_spent = Column(Float, default=0.0)  # in minutes

    # Relationships
    cycle = relationship("LearningCycle", back_populates="cycle_words")
    user_word = relationship("UserWord")


class UserLog(Base, TimestampMixin):
    """User-specific log messages."""
    __tablename__ = "user_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    category = Column(String(50))  # e.g., "word_added", "word_learned", "cycle_completed"

    # Relationships
    user = relationship("User", back_populates="logs") 