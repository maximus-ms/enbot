"""Tests for scheduler service."""
import asyncio
from datetime import datetime, timedelta
from typing import Generator

import pytest
from faker import Faker
from sqlalchemy.orm import Session
from telegram import Bot

from enbot.models.base import SessionLocal, init_db
from enbot.models.models import User, Word, UserWord, LearningCycle
from enbot.services.scheduler_service import SchedulerService

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
def mock_bot() -> Bot:
    """Create a mock Telegram bot."""
    return Bot(token="test_token")


@pytest.fixture
def scheduler_service(mock_bot: Bot) -> SchedulerService:
    """Create a scheduler service instance."""
    return SchedulerService(mock_bot)


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


@pytest.mark.asyncio
async def test_start_stop(scheduler_service: SchedulerService) -> None:
    """Test starting and stopping the scheduler service."""
    # Start service
    await scheduler_service.start()
    assert scheduler_service.running is True
    assert len(scheduler_service.tasks) == 4  # Daily, review, achievement, streak tasks
    
    # Stop service
    await scheduler_service.stop()
    assert scheduler_service.running is False
    assert len(scheduler_service.tasks) == 0


@pytest.mark.asyncio
async def test_daily_notifications(
    scheduler_service: SchedulerService,
    test_user: User,
    mock_bot: Bot,
) -> None:
    """Test daily notification task."""
    # Create test data
    word = Word(text="test")
    scheduler_service.db.add(word)
    scheduler_service.db.commit()
    
    user_word = UserWord(
        user_id=test_user.id,
        word_id=word.id,
        is_learned=True,
    )
    scheduler_service.db.add(user_word)
    scheduler_service.db.commit()
    
    # Start service
    await scheduler_service.start()
    
    # Run daily notifications task
    await scheduler_service._run_daily_notifications()
    
    # Check if message was sent
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args[1]
    assert call_args["chat_id"] == test_user.telegram_id
    assert "Good morning" in call_args["text"]
    
    # Stop service
    await scheduler_service.stop()


@pytest.mark.asyncio
async def test_review_reminders(
    scheduler_service: SchedulerService,
    test_user: User,
    mock_bot: Bot,
) -> None:
    """Test review reminder task."""
    # Create test data
    word = Word(text="test")
    scheduler_service.db.add(word)
    scheduler_service.db.commit()
    
    user_word = UserWord(
        user_id=test_user.id,
        word_id=word.id,
        next_review=datetime.utcnow() - timedelta(days=1),
    )
    scheduler_service.db.add(user_word)
    scheduler_service.db.commit()
    
    # Start service
    await scheduler_service.start()
    
    # Run review reminders task
    await scheduler_service._run_review_reminders()
    
    # Check if message was sent
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args[1]
    assert call_args["chat_id"] == test_user.telegram_id
    assert "Time for Review" in call_args["text"]
    
    # Stop service
    await scheduler_service.stop()


@pytest.mark.asyncio
async def test_achievement_checks(
    scheduler_service: SchedulerService,
    test_user: User,
    mock_bot: Bot,
) -> None:
    """Test achievement check task."""
    # Create test data
    for i in range(10):
        word = Word(text=f"word{i}")
        scheduler_service.db.add(word)
        scheduler_service.db.commit()
        
        user_word = UserWord(
            user_id=test_user.id,
            word_id=word.id,
            is_learned=True,
        )
        scheduler_service.db.add(user_word)
        scheduler_service.db.commit()
    
    # Start service
    await scheduler_service.start()
    
    # Run achievement checks task
    await scheduler_service._run_achievement_checks()
    
    # Check if message was sent
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args[1]
    assert call_args["chat_id"] == test_user.telegram_id
    assert "Achievement Unlocked" in call_args["text"]
    
    # Stop service
    await scheduler_service.stop()


@pytest.mark.asyncio
async def test_streak_checks(
    scheduler_service: SchedulerService,
    test_user: User,
    mock_bot: Bot,
) -> None:
    """Test streak check task."""
    # Create test data
    for i in range(7):
        cycle = LearningCycle(
            user_id=test_user.id,
            start_time=datetime.utcnow() - timedelta(days=i),
            end_time=datetime.utcnow() - timedelta(days=i),
            is_completed=True,
            words_learned=5,
            time_spent=10.0,
        )
        scheduler_service.db.add(cycle)
    scheduler_service.db.commit()
    
    # Start service
    await scheduler_service.start()
    
    # Run streak checks task
    await scheduler_service._run_streak_checks()
    
    # Check if message was sent
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args[1]
    assert call_args["chat_id"] == test_user.telegram_id
    assert "Amazing Streak" in call_args["text"]
    
    # Stop service
    await scheduler_service.stop()


@pytest.mark.asyncio
async def test_schedule_task(scheduler_service: SchedulerService) -> None:
    """Test scheduling a custom task."""
    # Define test coroutine
    async def test_coro():
        pass
    
    # Schedule task
    scheduler_service.schedule_task("test_task", test_coro, 60)
    
    # Check task was scheduled
    assert "test_task" in scheduler_service.tasks
    
    # Cancel task
    scheduler_service.cancel_task("test_task")
    
    # Check task was cancelled
    assert "test_task" not in scheduler_service.tasks


@pytest.mark.asyncio
async def test_error_handling(scheduler_service: SchedulerService, mock_bot: Bot) -> None:
    """Test error handling in tasks."""
    # Make bot.send_message raise an exception
    mock_bot.send_message.side_effect = Exception("Test error")
    
    # Start service
    await scheduler_service.start()
    
    # Run daily notifications task
    await scheduler_service._run_daily_notifications()
    
    # Check service is still running
    assert scheduler_service.running is True
    
    # Stop service
    await scheduler_service.stop()


if __name__ == "__main__":
    pytest.main([__file__]) 