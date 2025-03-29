"""Tests for database models."""
from datetime import datetime, timedelta
from typing import Generator

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from enbot.models.base import SessionLocal, init_db
from enbot.models.models import (
    CycleWord,
    Example,
    LearningCycle,
    User,
    UserLog,
    UserWord,
    Word,
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


def test_user_creation(db: Session) -> None:
    """Test user creation."""
    user = User(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
        native_language="uk",
        target_language="en",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert user.is_admin is False
    assert user.daily_goal_minutes == 10
    assert user.daily_goal_words == 5
    assert user.day_start_hour == 3


def test_word_creation(db: Session) -> None:
    """Test word creation."""
    word = Word(
        text="hello",
        translation="привіт",
        transcription="həˈləʊ",
        language_pair="en-uk",
    )
    db.add(word)
    db.commit()
    db.refresh(word)

    assert word.id is not None
    assert word.text == "hello"
    assert word.translation == "привіт"
    assert word.transcription == "həˈləʊ"
    assert word.language_pair == "en-uk"


def test_user_word_creation(db: Session) -> None:
    """Test user word creation."""
    # Create user and word first
    user = User(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
        native_language="uk",
        target_language="en",
    )
    word = Word(
        text="hello",
        translation="привіт",
        language_pair="en-uk",
    )
    db.add(user)
    db.add(word)
    db.commit()

    user_word = UserWord(
        user_id=user.id,
        word_id=word.id,
        priority=5,
        is_learned=False,
        last_reviewed=datetime.utcnow(),
        next_review=datetime.utcnow() + timedelta(days=1),
        review_stage=0,
    )
    db.add(user_word)
    db.commit()
    db.refresh(user_word)

    assert user_word.id is not None
    assert user_word.priority == 5
    assert user_word.is_learned is False
    assert user_word.review_stage == 0


def test_learning_cycle_creation(db: Session) -> None:
    """Test learning cycle creation."""
    user = User(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
        native_language="uk",
        target_language="en",
    )
    db.add(user)
    db.commit()

    cycle = LearningCycle(
        user_id=user.id,
        start_time=datetime.utcnow(),
        is_completed=False,
        words_learned=0,
        time_spent=0.0,
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)

    assert cycle.id is not None
    assert cycle.is_completed is False
    assert cycle.words_learned == 0
    assert cycle.time_spent == 0.0


def test_user_log_creation(db: Session) -> None:
    """Test user log creation."""
    user = User(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
        native_language="uk",
        target_language="en",
    )
    db.add(user)
    db.commit()

    log = UserLog(
        user_id=user.id,
        message="Test log message",
        level="INFO",
        category="test",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    assert log.id is not None
    assert log.message == "Test log message"
    assert log.level == "INFO"
    assert log.category == "test"


if __name__ == "__main__":
    pytest.main([__file__]) 