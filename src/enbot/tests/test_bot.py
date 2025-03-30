"""Tests for Telegram bot handlers."""
from datetime import datetime, timedelta, UTC
from typing import Generator
from unittest.mock import Mock, AsyncMock, patch

import pytest
from faker import Faker
from sqlalchemy.orm import Session
from telegram import Update, User as TelegramUser
from telegram.ext import CallbackContext, Application

from enbot.models.base import SessionLocal, init_db
from enbot.models.models import (
    CycleWord,
    LearningCycle,
    User,
    UserLog,
    UserWord,
    Word,
    Example,
)
from enbot.bot import (
    start,
    handle_callback,
    start_learning,
    add_words,
    handle_add_words,
    show_statistics,
    show_settings,
    handle_language_selection,
    MAIN_MENU,
    LEARNING,
    ADD_WORDS,
    SETTINGS,
    STATISTICS,
    LANGUAGE_SELECTION,
)

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
def telegram_user() -> Mock:
    """Create a mock Telegram user."""
    user = Mock(spec=TelegramUser)
    user.id = fake.random_int()
    user.first_name = fake.first_name()
    user.last_name = fake.last_name()
    user.username = f"test_user_{fake.random_int()}"  # Make username unique
    user.is_bot = False
    user.language_code = "en"
    user.is_premium = False
    user.added_to_attachment_menu = False
    return user


@pytest.fixture
def update(telegram_user: Mock) -> Mock:
    """Create a mock Update object."""
    update = AsyncMock(spec=Update)
    update.update_id = fake.random_int()
    update.effective_user = telegram_user
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.callback_query = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.fixture
def context() -> Mock:
    """Create a mock CallbackContext object."""
    context = AsyncMock(spec=CallbackContext)
    context.application = AsyncMock(spec=Application)
    return context


@pytest.mark.asyncio
async def test_start(update: Update, context: CallbackContext, db: Session) -> None:
    """Test start command handler."""
    # Create test user
    user = User(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
        native_language="uk",
        target_language="en",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Set callback_query to None to ensure message path is taken
    update.callback_query = None

    # Mock UserService
    mock_user_service = Mock()
    mock_user_service.get_or_create_user.return_value = user
    with patch('enbot.bot.UserService', return_value=mock_user_service):
        # Run handler
        result = await start(update, context)
        
        # Check database
        user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
        assert user is not None
        assert user.username == update.effective_user.username
        assert user.native_language == "uk"  # Default value from UserService
        assert user.target_language == "en"  # Default value from UserService
        
        # Check message
        update.message.reply_text.assert_called_once()
        assert "Welcome to EnBot" in update.message.reply_text.call_args[0][0]
        
        # Check return value
        assert result == MAIN_MENU


@pytest.mark.asyncio
async def test_handle_callback(db: Session):
    """Test handling callback queries."""
    # Create a test user
    user = User(
        telegram_id=fake.random_int(),
        username=f"test_user_{fake.random_int()}",
        native_language="en",
        target_language="es"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create mock update and context
    update = AsyncMock()
    update.effective_user = AsyncMock()
    update.effective_user.id = user.telegram_id
    update.effective_user.username = user.username
    update.callback_query = AsyncMock()
    update.callback_query.data = "start_learning"
    update.callback_query.from_user = update.effective_user
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()

    context = AsyncMock()

    # Mock get_user_from_update to return our test user
    with patch('enbot.bot.get_user_from_update', return_value=user):
        # Call handle_callback
        result = await handle_callback(update, context)

        # Verify callback was answered
        assert update.callback_query.answer.call_count == 1

        # Verify message was sent
        assert update.message.reply_text.call_count == 1


@pytest.mark.asyncio
async def test_start_learning(db: Session) -> None:
    """Test start learning handler."""
    # Create test data
    user = User(
        telegram_id=fake.random_int(),
        username=f"test_user_{fake.random_int()}",
        native_language="en",
        target_language="es",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create a test word
    word = Word(
        text="test",
        translation="prueba",
        language_pair="en-es"
    )
    db.add(word)
    db.commit()

    # Create an example for the word
    example = Example(
        word_id=word.id,
        sentence="This is a test.",
        translation="Esta es una prueba."
    )
    db.add(example)
    db.commit()
    
    # Create a user word
    user_word = UserWord(
        user_id=user.id,
        word_id=word.id,
        priority=5,
    )
    db.add(user_word)
    db.commit()
    
    # Create mock update and context
    update = AsyncMock()
    update.effective_user = AsyncMock()
    update.effective_user.id = user.telegram_id
    update.effective_user.username = user.username
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()

    context = AsyncMock()

    # Mock get_user_from_update to return our test user
    with patch('enbot.bot.get_user_from_update', return_value=user):
        # Run handler
        result = await start_learning(update, context)
        
        # Check message was sent
        assert update.message.reply_text.call_count == 1
        call_args = update.message.reply_text.call_args[0][0]
        assert "Let's learn some words!" in call_args
        assert "test" in call_args
        assert "prueba" in call_args
        assert "This is a test." in call_args
        
        # Check return value
        assert result == LEARNING

        # Verify a learning cycle was created
        cycle = db.query(LearningCycle).filter(LearningCycle.user_id == user.id).first()
        assert cycle is not None
        assert not cycle.is_completed

        # Verify words were added to the cycle
        cycle_words = db.query(CycleWord).filter(CycleWord.cycle_id == cycle.id).all()
        assert len(cycle_words) == 1
        assert cycle_words[0].user_word_id == user_word.id


@pytest.mark.asyncio
async def test_add_words(db: Session) -> None:
    """Test add words handler."""
    # Create test user
    user = User(
        telegram_id=fake.random_int(),
        username=f"test_user_{fake.random_int()}",
        native_language="en",
        target_language="es"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create mock update and context
    update = AsyncMock()
    update.effective_user = AsyncMock()
    update.effective_user.id = user.telegram_id
    update.effective_user.username = user.username
    update.callback_query = AsyncMock()
    update.callback_query.data = "add_words"
    update.callback_query.from_user = update.effective_user
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = AsyncMock()

    # Mock get_user_from_update to return our test user
    with patch('enbot.bot.get_user_from_update', return_value=user):
        # Run handler
        result = await add_words(update, context)
        
        # Check message was edited
        assert update.callback_query.edit_message_text.call_count == 1
        call_args = update.callback_query.edit_message_text.call_args[0][0]
        assert "Please enter words to add" in call_args
        
        # Check return value
        assert result == ADD_WORDS


@pytest.mark.asyncio
async def test_handle_add_words(db: Session) -> None:
    """Test handle add words handler."""
    # Create test user
    user = User(
        telegram_id=fake.random_int(),
        username=f"test_user_{fake.random_int()}",
        native_language="en",
        target_language="es",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create mock update and context
    update = AsyncMock()
    update.effective_user = AsyncMock()
    update.effective_user.id = user.telegram_id
    update.effective_user.username = user.username
    update.message = AsyncMock()
    update.message.text = "hello\nworld\npython"
    update.message.reply_text = AsyncMock()

    context = AsyncMock()

    # Mock get_user_from_update to return our test user
    with patch('enbot.bot.get_user_from_update', return_value=user):
        # Run handler
        result = await handle_add_words(update, context)
        
        # Check database
        user_words = db.query(UserWord).filter(UserWord.user_id == user.id).all()
        assert len(user_words) == 3
        words = [uw.word.text for uw in user_words]
        assert "hello" in words
        assert "world" in words
        assert "python" in words
        
        # Check message
        assert update.message.reply_text.call_count == 1
        call_args = update.message.reply_text.call_args[0][0]
        assert "Successfully added 3 words" in call_args
        
        # Check return value
        assert result == MAIN_MENU


@pytest.mark.asyncio
async def test_show_statistics(db: Session) -> None:
    """Test show statistics handler."""
    # Create test user
    user = User(
        telegram_id=fake.random_int(),
        username=f"test_user_{fake.random_int()}",
        native_language="en",
        target_language="es",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create some completed cycles
    for _ in range(3):
        cycle = LearningCycle(
            user_id=user.id,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            is_completed=True,
            words_learned=5,
            time_spent=10.0,
        )
        db.add(cycle)
    db.commit()
    
    # Create mock update and context
    update = AsyncMock()
    update.effective_user = AsyncMock()
    update.effective_user.id = user.telegram_id
    update.effective_user.username = user.username
    update.callback_query = AsyncMock()
    update.callback_query.data = "statistics"
    update.callback_query.from_user = update.effective_user
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = AsyncMock()

    # Mock get_user_from_update to return our test user
    with patch('enbot.bot.get_user_from_update', return_value=user):
        # Run handler
        result = await show_statistics(update, context)
        
        # Check message was edited
        assert update.callback_query.edit_message_text.call_count == 1
        call_args = update.callback_query.edit_message_text.call_args[0][0]
        assert "Your Learning Statistics" in call_args
        assert "Total Words Learned: 15" in call_args
        assert "Total Time Spent: 30.0" in call_args
        assert "Total Learning Cycles: 3" in call_args
        
        # Check return value
        assert result == MAIN_MENU


@pytest.mark.asyncio
async def test_show_settings(db: Session) -> None:
    """Test show settings handler."""
    # Create test user
    user = User(
        telegram_id=fake.random_int(),
        username=f"test_user_{fake.random_int()}",
        native_language="en",
        target_language="es",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create mock update and context
    update = AsyncMock()
    update.effective_user = AsyncMock()
    update.effective_user.id = user.telegram_id
    update.effective_user.username = user.username
    update.callback_query = AsyncMock()
    update.callback_query.data = "settings"
    update.callback_query.from_user = update.effective_user
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = AsyncMock()

    # Mock get_user_from_update to return our test user
    with patch('enbot.bot.get_user_from_update', return_value=user):
        # Run handler
        result = await show_settings(update, context)
        
        # Check message was edited
        assert update.callback_query.edit_message_text.call_count == 1
        call_args = update.callback_query.edit_message_text.call_args[0][0]
        assert "Settings" in call_args
        assert "What would you like to change?" in call_args
        
        # Check return value
        assert result == SETTINGS


@pytest.mark.asyncio
async def test_handle_language_selection(db: Session) -> None:
    """Test handle language selection handler."""
    # Create test user
    user = User(
        telegram_id=fake.random_int(),
        username=f"test_user_{fake.random_int()}",
        native_language="en",
        target_language="es",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Store user ID for later use
    user_id = user.id
    
    # Create mock update and context
    update = AsyncMock()
    update.effective_user = AsyncMock()
    update.effective_user.id = user.telegram_id
    update.effective_user.username = user.username
    update.callback_query = AsyncMock()
    update.callback_query.data = "language_fr"
    update.callback_query.from_user = update.effective_user
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = AsyncMock()

    # Mock get_user_from_update and SessionLocal to return our test user and session
    with patch('enbot.bot.get_user_from_update', return_value=user), \
         patch('enbot.bot.SessionLocal', return_value=db):
        # Run handler
        result = await handle_language_selection(update, context)
        
        # Check database
        updated_user = db.query(User).filter(User.id == user_id).first()
        assert updated_user.target_language == "fr"
        
        # Check message was edited
        assert update.callback_query.edit_message_text.call_count == 1
        call_args = update.callback_query.edit_message_text.call_args[0][0]
        assert "Language settings updated successfully" in call_args
        
        # Check return value
        assert result == MAIN_MENU


if __name__ == "__main__":
    pytest.main([__file__]) 