"""Tests for database models."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from enbot.models.base import Base, SessionLocal, engine
from enbot.models.models import (
    LearningCycle,
    User,
    UserLog,
    UserWord,
    Word,
)


@pytest.fixture(scope="function")
def db() -> Session:
    """Create a test database."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop tables
        Base.metadata.drop_all(bind=engine)


def test_user_creation(db: Session) -> None:
    """Test user creation."""
    user = User(
        telegram_id=123456789,
        username="test_user",
        native_language="en",
        target_language="uk",
        is_admin=True,
        daily_goal_minutes=15,
        daily_goal_words=7,
        day_start_hour=4,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    assert user.telegram_id == 123456789
    assert user.username == "test_user"
    assert user.native_language == "en"
    assert user.target_language == "uk"
    assert user.is_admin is True
    assert user.daily_goal_minutes == 15
    assert user.daily_goal_words == 7
    assert user.day_start_hour == 4
    assert user.created_at is not None
    assert user.updated_at is not None


def test_word_creation(db: Session) -> None:
    """Test word creation."""
    word = Word(
        text="test",
        translation="тест",
        transcription="test",
        pronunciation_file="test.mp3",
        image_file="test.jpg",
        language_pair="en-uk",
    )
    db.add(word)
    db.commit()
    db.refresh(word)
    
    assert word.text == "test"
    assert word.translation == "тест"
    assert word.transcription == "test"
    assert word.pronunciation_file == "test.mp3"
    assert word.image_file == "test.jpg"
    assert word.language_pair == "en-uk"
    assert word.created_at is not None
    assert word.updated_at is not None


def test_user_word_creation(db: Session) -> None:
    """Test user word creation."""
    # Create user and word
    user = User(
        telegram_id=123456789,
        native_language="en",
        target_language="uk",
    )
    word = Word(
        text="test",
        translation="тест",
        language_pair="en-uk",
    )
    db.add_all([user, word])
    db.commit()
    
    # Create user word
    user_word = UserWord(
        user_id=user.id,
        word_id=word.id,
        priority=3,
        is_learned=False,
        last_reviewed=datetime.now(UTC),
        next_review=datetime.now(UTC) + timedelta(days=1),
        review_stage=1,
    )
    db.add(user_word)
    db.commit()
    db.refresh(user_word)
    
    assert user_word.user_id == user.id
    assert user_word.word_id == word.id
    assert user_word.priority == 3
    assert user_word.is_learned is False
    assert user_word.last_reviewed is not None
    assert user_word.next_review is not None
    assert user_word.review_stage == 1
    assert user_word.created_at is not None
    assert user_word.updated_at is not None


def test_learning_cycle_creation(db: Session) -> None:
    """Test learning cycle creation."""
    # Create user
    user = User(
        telegram_id=123456789,
        native_language="en",
        target_language="uk",
    )
    db.add(user)
    db.commit()
    
    # Create learning cycle
    cycle = LearningCycle(
        user_id=user.id,
        start_time=datetime.now(UTC),
        is_completed=False,
        words_learned=5,
        time_spent=15.5,
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    
    assert cycle.user_id == user.id
    assert cycle.start_time is not None
    assert cycle.end_time is None
    assert cycle.is_completed is False
    assert cycle.words_learned == 5
    assert cycle.time_spent == 15.5
    assert cycle.created_at is not None
    assert cycle.updated_at is not None


def test_user_log_creation(db: Session) -> None:
    """Test user log creation."""
    # Create user
    user = User(
        telegram_id=123456789,
        native_language="en",
        target_language="uk",
    )
    db.add(user)
    db.commit()
    
    # Create user log
    log = UserLog(
        user_id=user.id,
        message="Word 'test' learned successfully",
        level="INFO",
        category="word_learned",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    assert log.user_id == user.id
    assert log.message == "Word 'test' learned successfully"
    assert log.level == "INFO"
    assert log.category == "word_learned"
    assert log.created_at is not None
    assert log.updated_at is not None


if __name__ == "__main__":
    pytest.main([__file__])