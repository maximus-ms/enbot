"""Tests for Telegram bot handlers."""
from datetime import datetime, timedelta
from typing import Generator

import pytest
from faker import Faker
from sqlalchemy.orm import Session
from telegram import Update, User as TelegramUser
from telegram.ext import CallbackContext

from enbot.models.base import SessionLocal, init_db
from enbot.models.models import (
    CycleWord,
    LearningCycle,
    User,
    UserLog,
    UserWord,
    Word,
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
def telegram_user() -> TelegramUser:
    """Create a mock Telegram user."""
    return TelegramUser(
        id=fake.random_int(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        username=fake.user_name(),
        is_bot=False,
        language_code="en",
        is_premium=False,
        added_to_attachment_menu=False,
    )


@pytest.fixture
def update(telegram_user: TelegramUser) -> Update:
    """Create a mock Update object."""
    update = Update(update_id=fake.random_int())
    update.effective_user = telegram_user
    return update


@pytest.fixture
def context() -> CallbackContext:
    """Create a mock CallbackContext object."""
    return CallbackContext(Application.builder().token("test_token").build())


def test_start(update: Update, context: CallbackContext, db: Session) -> None:
    """Test start command handler."""
    # Add message to update
    update.message = type("Message", (), {"reply_text": pytest.AsyncMock()})()
    
    # Run handler
    result = pytest.mark.asyncio(start(update, context))
    
    # Check database
    user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
    assert user is not None
    assert user.username == update.effective_user.username
    
    # Check message
    update.message.reply_text.assert_called_once()
    assert "Welcome to EnBot" in update.message.reply_text.call_args[0][0]
    
    # Check return value
    assert result == MAIN_MENU


def test_handle_callback(update: Update, context: CallbackContext) -> None:
    """Test callback query handler."""
    # Add callback query to update
    update.callback_query = type("CallbackQuery", (), {
        "answer": pytest.AsyncMock(),
        "data": "start_learning",
        "edit_message_text": pytest.AsyncMock(),
    })()
    
    # Run handler
    result = pytest.mark.asyncio(handle_callback(update, context))
    
    # Check callback was answered
    update.callback_query.answer.assert_called_once()
    
    # Check message was edited
    update.callback_query.edit_message_text.assert_called_once()
    
    # Check return value
    assert result == LEARNING


def test_start_learning(update: Update, context: CallbackContext, db: Session) -> None:
    """Test start learning handler."""
    # Create test data
    user = User(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )
    db.add(user)
    db.commit()
    
    word = Word(text="test")
    db.add(word)
    db.commit()
    
    user_word = UserWord(
        user_id=user.id,
        word_id=word.id,
        priority=5,
    )
    db.add(user_word)
    db.commit()
    
    # Add callback query to update
    update.callback_query = type("CallbackQuery", (), {
        "answer": pytest.AsyncMock(),
        "edit_message_text": pytest.AsyncMock(),
    })()
    
    # Run handler
    result = pytest.mark.asyncio(start_learning(update, context))
    
    # Check message was edited
    update.callback_query.edit_message_text.assert_called_once()
    assert "Let's learn: test" in update.callback_query.edit_message_text.call_args[0][0]
    
    # Check return value
    assert result == LEARNING


def test_add_words(update: Update, context: CallbackContext) -> None:
    """Test add words handler."""
    # Add callback query to update
    update.callback_query = type("CallbackQuery", (), {
        "answer": pytest.AsyncMock(),
        "edit_message_text": pytest.AsyncMock(),
    })()
    
    # Run handler
    result = pytest.mark.asyncio(add_words(update, context))
    
    # Check message was edited
    update.callback_query.edit_message_text.assert_called_once()
    assert "Please enter words to add" in update.callback_query.edit_message_text.call_args[0][0]
    
    # Check return value
    assert result == ADD_WORDS


def test_handle_add_words(update: Update, context: CallbackContext, db: Session) -> None:
    """Test handle add words handler."""
    # Create test user
    user = User(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )
    db.add(user)
    db.commit()
    
    # Add message to update
    update.message = type("Message", (), {
        "text": "hello\nworld\npython",
        "reply_text": pytest.AsyncMock(),
    })()
    
    # Run handler
    result = pytest.mark.asyncio(handle_add_words(update, context))
    
    # Check database
    user_words = db.query(UserWord).filter(UserWord.user_id == user.id).all()
    assert len(user_words) == 3
    
    # Check message
    update.message.reply_text.assert_called_once()
    assert "Successfully added 3 words" in update.message.reply_text.call_args[0][0]
    
    # Check return value
    assert result == MAIN_MENU


def test_show_statistics(update: Update, context: CallbackContext, db: Session) -> None:
    """Test show statistics handler."""
    # Create test data
    user = User(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )
    db.add(user)
    db.commit()
    
    # Create some completed cycles
    for _ in range(3):
        cycle = LearningCycle(
            user_id=user.id,
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
            is_completed=True,
            words_learned=5,
            time_spent=10.0,
        )
        db.add(cycle)
    db.commit()
    
    # Add callback query to update
    update.callback_query = type("CallbackQuery", (), {
        "answer": pytest.AsyncMock(),
        "edit_message_text": pytest.AsyncMock(),
    })()
    
    # Run handler
    result = pytest.mark.asyncio(show_statistics(update, context))
    
    # Check message was edited
    update.callback_query.edit_message_text.assert_called_once()
    assert "Your Learning Statistics" in update.callback_query.edit_message_text.call_args[0][0]
    
    # Check return value
    assert result == MAIN_MENU


def test_show_settings(update: Update, context: CallbackContext) -> None:
    """Test show settings handler."""
    # Add callback query to update
    update.callback_query = type("CallbackQuery", (), {
        "answer": pytest.AsyncMock(),
        "edit_message_text": pytest.AsyncMock(),
    })()
    
    # Run handler
    result = pytest.mark.asyncio(show_settings(update, context))
    
    # Check message was edited
    update.callback_query.edit_message_text.assert_called_once()
    assert "Settings" in update.callback_query.edit_message_text.call_args[0][0]
    
    # Check return value
    assert result == SETTINGS


def test_handle_language_selection(update: Update, context: CallbackContext, db: Session) -> None:
    """Test handle language selection handler."""
    # Create test user
    user = User(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )
    db.add(user)
    db.commit()
    
    # Add callback query to update
    update.callback_query = type("CallbackQuery", (), {
        "answer": pytest.AsyncMock(),
        "edit_message_text": pytest.AsyncMock(),
        "data": "language_en",
    })()
    
    # Run handler
    result = pytest.mark.asyncio(handle_language_selection(update, context))
    
    # Check database
    updated_user = db.query(User).filter(User.id == user.id).first()
    assert updated_user.target_language == "en"
    
    # Check message was edited
    update.callback_query.edit_message_text.assert_called_once()
    assert "Language settings updated successfully" in update.callback_query.edit_message_text.call_args[0][0]
    
    # Check return value
    assert result == MAIN_MENU


if __name__ == "__main__":
    pytest.main([__file__]) 