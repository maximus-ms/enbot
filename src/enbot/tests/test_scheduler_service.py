"""Tests for scheduler service."""
import asyncio
from datetime import datetime, timedelta, UTC
from typing import Generator
from unittest.mock import Mock, patch

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
def mock_bot() -> Mock:
    """Create a mock Telegram bot."""
    bot = Mock(spec=Bot)
    bot.token = "test_token"
    return bot


@pytest.fixture
def scheduler_service(mock_bot: Mock, db: Session) -> SchedulerService:
    """Create a scheduler service instance."""
    return SchedulerService(mock_bot, db)


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
        native_language="en",
        target_language="uk",
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
    mock_bot: Mock,
) -> None:
    """Test daily notification task."""
    # Create test data
    word = Word(
        text="test",
        translation="тест",
        language_pair="en-uk"
    )
    scheduler_service.db.add(word)
    scheduler_service.db.commit()
    
    user_word = UserWord(
        user_id=test_user.id,
        word_id=word.id,
        is_learned=True,
    )
    scheduler_service.db.add(user_word)
    scheduler_service.db.commit()
    
    # Mock current time to match user's day_start_hour
    mock_time = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)  # 9:00 AM UTC
    
    # Mock datetime.now(UTC) in all modules
    with patch("enbot.models.models.datetime") as mock_models_datetime, \
         patch("enbot.services.notification_service.datetime") as mock_notification_datetime, \
         patch("enbot.services.scheduler_service.datetime") as mock_scheduler_datetime, \
         patch("enbot.services.word_service.datetime") as mock_word_datetime:
        mock_models_datetime.now.return_value = mock_time
        mock_notification_datetime.now.return_value = mock_time
        mock_scheduler_datetime.now.return_value = mock_time
        mock_word_datetime.now.return_value = mock_time
        
        # Set running flag to True
        scheduler_service.running = True
        
        # Run daily notifications task with timeout
        try:
            await asyncio.wait_for(
                scheduler_service._run_daily_notifications(),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            # This is expected since the task runs in an infinite loop
            pass
    
    # Check if message was sent
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args[1]
    assert call_args["chat_id"] == test_user.telegram_id
    assert "Good morning" in call_args["text"]


@pytest.mark.asyncio
async def test_review_reminders(
    scheduler_service: SchedulerService,
    test_user: User,
    mock_bot: Mock,
) -> None:
    """Test review reminder task."""
    # Create test data
    word = Word(
        text="test",
        translation="тест",
        language_pair="en-uk"
    )
    scheduler_service.db.add(word)
    scheduler_service.db.commit()
    
    # Mock current time for creating user_word
    mock_time = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)  # 9:00 AM UTC
    
    user_word = UserWord(
        user_id=test_user.id,
        word_id=word.id,
        is_learned=True,
        next_review=mock_time - timedelta(days=1),
    )
    scheduler_service.db.add(user_word)
    scheduler_service.db.commit()
    
    # Mock datetime.now(UTC) in all modules
    with patch("enbot.models.models.datetime") as mock_models_datetime, \
         patch("enbot.services.notification_service.datetime") as mock_notification_datetime, \
         patch("enbot.services.scheduler_service.datetime") as mock_scheduler_datetime, \
         patch("enbot.services.word_service.datetime") as mock_word_datetime:
        # Mock datetime.now and UTC
        for mock_datetime in [mock_models_datetime, mock_notification_datetime, mock_scheduler_datetime, mock_word_datetime]:
            mock_datetime.now.return_value = mock_time
            mock_datetime.UTC = UTC
        
        # Set running flag to True
        scheduler_service.running = True
        
        # Debug: Check user's notification settings
        print(f"\nDebug: User notifications enabled: {test_user.notifications_enabled}")
        
        # Debug: Check words for review
        words_for_review = scheduler_service.notification_service.word_service.get_words_for_review(test_user.id)
        print(f"Debug: Words for review: {words_for_review}")
        
        # Debug: Check active cycles
        active_cycle = (
            scheduler_service.db.query(LearningCycle)
            .filter(
                LearningCycle.user_id == test_user.id,
                LearningCycle.is_completed == False,
            )
            .first()
        )
        print(f"Debug: Active cycle: {active_cycle}")
        
        # Debug: Check last notification time
        print(f"Debug: Last notification time: {test_user.last_notification_time}")
        
        # Run review reminders task with timeout
        try:
            await asyncio.wait_for(
                scheduler_service._run_review_reminders(),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            # This is expected since the task runs in an infinite loop
            pass
        
        # Check if message was sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args[1]
        assert call_args["chat_id"] == test_user.telegram_id
        assert "Time for Review" in call_args["text"]


@pytest.mark.asyncio
async def test_achievement_checks(
    scheduler_service: SchedulerService,
    test_user: User,
    mock_bot: Mock,
) -> None:
    """Test achievement check task."""
    # Create test data
    for i in range(10):
        word = Word(
            text=f"word{i}",
            translation=f"слово{i}",
            language_pair="en-uk"
        )
        scheduler_service.db.add(word)
        scheduler_service.db.commit()
        
        user_word = UserWord(
            user_id=test_user.id,
            word_id=word.id,
            is_learned=True,
        )
        scheduler_service.db.add(user_word)
        scheduler_service.db.commit()
    
    # Mock current time
    mock_time = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)  # 9:00 AM UTC
    
    # Mock datetime.now(UTC) in all modules
    with patch("enbot.models.models.datetime") as mock_models_datetime, \
         patch("enbot.services.notification_service.datetime") as mock_notification_datetime, \
         patch("enbot.services.scheduler_service.datetime") as mock_scheduler_datetime, \
         patch("enbot.services.word_service.datetime") as mock_word_datetime:
        mock_models_datetime.now.return_value = mock_time
        mock_notification_datetime.now.return_value = mock_time
        mock_scheduler_datetime.now.return_value = mock_time
        mock_word_datetime.now.return_value = mock_time
        
        # Set running flag to True
        scheduler_service.running = True
        
        # Run achievement checks task with timeout
        try:
            await asyncio.wait_for(
                scheduler_service._run_achievement_checks(),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            # This is expected since the task runs in an infinite loop
            pass
        
        # Check if message was sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args[1]
        assert call_args["chat_id"] == test_user.telegram_id
        assert "Achievement Unlocked" in call_args["text"]


@pytest.mark.asyncio
async def test_streak_checks(
    scheduler_service: SchedulerService,
    test_user: User,
    mock_bot: Mock,
) -> None:
    """Test streak check task."""
    # Create test data
    for i in range(7):
        cycle = LearningCycle(
            user_id=test_user.id,
            start_time=datetime.now(UTC) - timedelta(days=i),
            end_time=datetime.now(UTC) - timedelta(days=i),
            is_completed=True,
            words_learned=5,
            time_spent=10.0,
        )
        scheduler_service.db.add(cycle)
    scheduler_service.db.commit()
    
    # Mock current time
    mock_time = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)  # 9:00 AM UTC
    
    # Mock datetime.now(UTC) in all modules
    with patch("enbot.models.models.datetime") as mock_models_datetime, \
         patch("enbot.services.notification_service.datetime") as mock_notification_datetime, \
         patch("enbot.services.scheduler_service.datetime") as mock_scheduler_datetime, \
         patch("enbot.services.word_service.datetime") as mock_word_datetime:
        mock_models_datetime.now.return_value = mock_time
        mock_notification_datetime.now.return_value = mock_time
        mock_scheduler_datetime.now.return_value = mock_time
        mock_word_datetime.now.return_value = mock_time
        
        # Set running flag to True
        scheduler_service.running = True
        
        # Run streak checks task with timeout
        try:
            await asyncio.wait_for(
                scheduler_service._run_streak_checks(),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            # This is expected since the task runs in an infinite loop
            pass
        
        # Check if message was sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args[1]
        assert call_args["chat_id"] == test_user.telegram_id
        assert "Amazing Streak" in call_args["text"]


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
async def test_error_handling(scheduler_service: SchedulerService, mock_bot: Mock) -> None:
    """Test error handling in tasks."""
    # Make bot.send_message raise an exception
    mock_bot.send_message.side_effect = Exception("Test error")
    
    # Mock current time
    mock_time = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)  # 9:00 AM UTC
    
    # Mock datetime.now(UTC) in all modules
    with patch("enbot.models.models.datetime") as mock_models_datetime, \
         patch("enbot.services.notification_service.datetime") as mock_notification_datetime, \
         patch("enbot.services.scheduler_service.datetime") as mock_scheduler_datetime, \
         patch("enbot.services.word_service.datetime") as mock_word_datetime:
        mock_models_datetime.now.return_value = mock_time
        mock_notification_datetime.now.return_value = mock_time
        mock_scheduler_datetime.now.return_value = mock_time
        mock_word_datetime.now.return_value = mock_time
        
        # Set running flag to True
        scheduler_service.running = True
        
        # Run daily notifications task with timeout
        try:
            await asyncio.wait_for(
                scheduler_service._run_daily_notifications(),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            # This is expected since the task runs in an infinite loop
            pass
        
        # Check service is still running
        assert scheduler_service.running is True


if __name__ == "__main__":
    pytest.main([__file__]) 