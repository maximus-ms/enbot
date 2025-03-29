"""Tests for user service."""
from datetime import datetime, timedelta, UTC
from typing import Generator

import pytest
from faker import Faker
from sqlalchemy import and_
from sqlalchemy.orm import Session

from enbot.models.base import SessionLocal, init_db
from enbot.models.models import (
    CycleWord,
    LearningCycle,
    User,
    UserLog,
    UserWord,
    Word,
)
from enbot.services.user_service import UserService

fake = Faker()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def user_service(db: Session) -> UserService:
    """Create a user service instance."""
    return UserService(db)


def test_get_or_create_user(user_service: UserService) -> None:
    """Test user creation and retrieval."""
    # Create new user
    telegram_id = fake.random_int()
    username = fake.user_name()
    user = user_service.get_or_create_user(
        telegram_id=telegram_id,
        username=username,
        native_language="uk",
        target_language="en",
    )
    
    assert user.telegram_id == telegram_id
    assert user.username == username
    assert user.native_language == "uk"
    assert user.target_language == "en"
    
    # Get existing user
    existing_user = user_service.get_or_create_user(
        telegram_id=telegram_id,
        username="new_username",  # Should not update
    )
    
    assert existing_user.id == user.id
    assert existing_user.username == username  # Should not change


def test_update_user_settings(user_service: UserService) -> None:
    """Test updating user settings."""
    # Create user
    user = user_service.get_or_create_user(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
    )
    
    # Update settings
    updated_user = user_service.update_user_settings(
        user_id=user.id,
        native_language="ru",
        target_language="de",
        daily_goal_minutes=15,
        daily_goal_words=10,
        day_start_hour=4,
    )
    
    assert updated_user.native_language == "ru"
    assert updated_user.target_language == "de"
    assert updated_user.daily_goal_minutes == 15
    assert updated_user.daily_goal_words == 10
    assert updated_user.day_start_hour == 4


def test_add_words(user_service: UserService) -> None:
    """Test adding words to user's dictionary."""
    # Create user
    user = user_service.get_or_create_user(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
    )
    
    # Add words
    words = ["hello", "world", "python"]
    added_words = user_service.add_words(user.id, words, priority=5)
    
    assert len(added_words) == 3
    for user_word in added_words:
        assert user_word.user_id == user.id
        assert user_word.priority == 5
        assert user_word.is_learned is False
        assert user_word.review_stage == 0
    
    # Try to add same words again
    duplicate_words = user_service.add_words(user.id, words, priority=3)
    assert len(duplicate_words) == 0  # Should not add duplicates
    
    # Try to add with higher priority
    higher_priority_words = user_service.add_words(user.id, words, priority=7)
    assert len(higher_priority_words) == 3  # Should update priority


def test_get_user_statistics(user_service: UserService) -> None:
    """Test getting user statistics."""
    # Create user
    user = user_service.get_or_create_user(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
    )
    
    # Create some completed cycles
    for _ in range(3):
        cycle = LearningCycle(
            user_id=user.id,
            start_time=datetime.now(UTC) - timedelta(days=1),
            end_time=datetime.now(UTC),
            is_completed=True,
            words_learned=5,
            time_spent=10.0,
        )
        user_service.db.add(cycle)
    user_service.db.commit()
    
    # Get statistics
    stats = user_service.get_user_statistics(user.id, days=30)
    
    assert stats["total_words"] == 15
    assert stats["total_time_minutes"] == 30.0
    assert stats["total_cycles"] == 3
    assert stats["average_words_per_cycle"] == 5.0
    assert stats["average_time_per_cycle"] == 10.0


def test_log_user_activity(user_service: UserService) -> None:
    """Test logging user activity."""
    # Create user
    user = user_service.get_or_create_user(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
    )
    
    # Log activity
    message = "Test activity"
    level = "INFO"
    category = "test"
    
    user_service.log_user_activity(user.id, message, level, category)
    
    # Check log entry
    log = (
        user_service.db.query(UserLog)
        .filter(
            and_(
                UserLog.user_id == user.id,
                UserLog.message == message,
                UserLog.level == level,
                UserLog.category == category,
            )
        )
        .first()
    )
    assert log is not None


if __name__ == "__main__":
    pytest.main([__file__]) 