"""Tests for notification service."""
from datetime import datetime, timedelta
from typing import Generator

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from enbot.models.base import SessionLocal, init_db
from enbot.models.models import User, Word, UserWord, LearningCycle
from enbot.services.notification_service import NotificationService

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
def notification_service(db: Session) -> NotificationService:
    """Create a notification service instance."""
    return NotificationService(db)


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
        notifications_enabled=True,
        day_start_hour=9,
        daily_goal_words=10,
        daily_goal_minutes=15,
    )
    db.add(user)
    db.commit()
    return user


def test_get_users_for_notification(notification_service: NotificationService, test_user: User) -> None:
    """Test getting users for notification."""
    # Set current hour to match user's day_start_hour
    current_hour = 9
    
    # Get users
    users = notification_service.get_users_for_notification()
    assert len(users) == 1
    assert users[0].id == test_user.id
    
    # Disable notifications
    test_user.notifications_enabled = False
    notification_service.db.commit()
    
    # Get users again
    users = notification_service.get_users_for_notification()
    assert len(users) == 0


def test_get_daily_reminder_message(notification_service: NotificationService, test_user: User) -> None:
    """Test generating daily reminder message."""
    # Create some words
    word = Word(text="test")
    notification_service.db.add(word)
    notification_service.db.commit()
    
    user_word = UserWord(
        user_id=test_user.id,
        word_id=word.id,
        is_learned=True,
    )
    notification_service.db.add(user_word)
    notification_service.db.commit()
    
    # Create active cycle
    cycle = LearningCycle(
        user_id=test_user.id,
        start_time=datetime.utcnow(),
        is_completed=False,
        words_learned=5,
        time_spent=7.5,
    )
    notification_service.db.add(cycle)
    notification_service.db.commit()
    
    # Get message
    message = notification_service.get_daily_reminder_message(test_user)
    
    # Check message content
    assert "Good morning" in message
    assert "Total Words: 1" in message
    assert "Learned Words: 1" in message
    assert "Progress: 100.0%" in message
    assert "Words to Learn: 5/10" in message
    assert "Time Spent: 7.5/15" in message


def test_get_review_reminder_message(notification_service: NotificationService, test_user: User) -> None:
    """Test generating review reminder message."""
    # Create words for review
    word = Word(text="test")
    notification_service.db.add(word)
    notification_service.db.commit()
    
    user_word = UserWord(
        user_id=test_user.id,
        word_id=word.id,
        next_review=datetime.utcnow() - timedelta(days=1),
    )
    notification_service.db.add(user_word)
    notification_service.db.commit()
    
    # Get message
    message = notification_service.get_review_reminder_message(test_user)
    
    # Check message content
    assert "Time for Review" in message
    assert "You have 1 words to review" in message
    assert "• test" in message


def test_get_achievement_message(notification_service: NotificationService, test_user: User) -> None:
    """Test generating achievement message."""
    # Create learned words
    for i in range(10):
        word = Word(text=f"word{i}")
        notification_service.db.add(word)
        notification_service.db.commit()
        
        user_word = UserWord(
            user_id=test_user.id,
            word_id=word.id,
            is_learned=True,
        )
        notification_service.db.add(user_word)
        notification_service.db.commit()
    
    # Get message
    message = notification_service.get_achievement_message(test_user)
    
    # Check message content
    assert "Achievement Unlocked" in message
    assert "You've learned your first 10 words" in message


def test_get_streak_message(notification_service: NotificationService, test_user: User) -> None:
    """Test generating streak message."""
    # Create completed cycles for 7 days
    for i in range(7):
        cycle = LearningCycle(
            user_id=test_user.id,
            start_time=datetime.utcnow() - timedelta(days=i),
            end_time=datetime.utcnow() - timedelta(days=i),
            is_completed=True,
            words_learned=5,
            time_spent=10.0,
        )
        notification_service.db.add(cycle)
    notification_service.db.commit()
    
    # Get message
    message = notification_service.get_streak_message(test_user)
    
    # Check message content
    assert "Amazing Streak" in message
    assert "7 days in a row" in message


def test_should_send_review_reminder(notification_service: NotificationService, test_user: User) -> None:
    """Test checking if review reminder should be sent."""
    # Initially should send reminder
    assert notification_service.should_send_review_reminder(test_user) is True
    
    # Create words for review
    word = Word(text="test")
    notification_service.db.add(word)
    notification_service.db.commit()
    
    user_word = UserWord(
        user_id=test_user.id,
        word_id=word.id,
        next_review=datetime.utcnow() - timedelta(days=1),
    )
    notification_service.db.add(user_word)
    notification_service.db.commit()
    
    # Should send reminder with words to review
    assert notification_service.should_send_review_reminder(test_user) is True
    
    # Create active cycle
    cycle = LearningCycle(
        user_id=test_user.id,
        start_time=datetime.utcnow(),
        is_completed=False,
    )
    notification_service.db.add(cycle)
    notification_service.db.commit()
    
    # Should not send reminder while user is learning
    assert notification_service.should_send_review_reminder(test_user) is False
    
    # Update last notification time
    notification_service.update_last_notification_time(test_user)
    
    # Should not send reminder on same day
    assert notification_service.should_send_review_reminder(test_user) is False


def test_update_last_notification_time(notification_service: NotificationService, test_user: User) -> None:
    """Test updating last notification time."""
    # Update time
    notification_service.update_last_notification_time(test_user)
    
    # Check time was updated
    assert test_user.last_notification_time is not None
    assert (datetime.utcnow() - test_user.last_notification_time).total_seconds() < 1


if __name__ == "__main__":
    pytest.main([__file__]) 