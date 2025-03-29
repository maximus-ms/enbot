"""Tests for learning service."""
from datetime import datetime, timedelta
from typing import Generator

import pytest
from faker import Faker
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
from enbot.services.learning_service import LearningService

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
def learning_service(db: Session) -> LearningService:
    """Create a learning service instance."""
    return LearningService(db)


@pytest.fixture
def user(db: Session) -> User:
    """Create a test user."""
    user = User(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
        native_language="uk",
        target_language="en",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def word(db: Session) -> Word:
    """Create a test word."""
    word = Word(
        text="hello",
        translation="привіт",
        language_pair="en-uk",
    )
    db.add(word)
    db.commit()
    db.refresh(word)
    return word


@pytest.fixture
def user_word(db: Session, user: User, word: Word) -> UserWord:
    """Create a test user word."""
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
    return user_word


def test_get_active_cycle(
    learning_service: LearningService, user: User
) -> None:
    """Test getting active cycle."""
    # No active cycle should exist initially
    assert learning_service.get_active_cycle(user.id) is None

    # Create a new cycle
    cycle = learning_service.create_new_cycle(user.id)
    assert cycle is not None
    assert cycle.user_id == user.id
    assert cycle.is_completed is False

    # Get active cycle
    active_cycle = learning_service.get_active_cycle(user.id)
    assert active_cycle is not None
    assert active_cycle.id == cycle.id


def test_get_words_for_cycle(
    learning_service: LearningService, user: User, user_word: UserWord
) -> None:
    """Test getting words for a cycle."""
    # Create some repetition words
    for _ in range(5):
        word = Word(
            text=fake.word(),
            translation=fake.word(),
            language_pair="en-uk",
        )
        db.add(word)
        db.commit()
        db.refresh(word)

        user_word = UserWord(
            user_id=user.id,
            word_id=word.id,
            priority=11,  # repetition priority
            is_learned=False,
            last_reviewed=datetime.utcnow() - timedelta(days=2),
            next_review=datetime.utcnow() - timedelta(days=1),
            review_stage=0,
        )
        db.add(user_word)
    db.commit()

    # Get words for cycle
    words = learning_service.get_words_for_cycle(user.id, cycle_size=10)
    assert len(words) <= 10
    assert all(isinstance(word, UserWord) for word in words)


def test_add_words_to_cycle(
    learning_service: LearningService, user: User, user_word: UserWord
) -> None:
    """Test adding words to a cycle."""
    # Create a new cycle
    cycle = learning_service.create_new_cycle(user.id)
    
    # Add words to cycle
    cycle_words = learning_service.add_words_to_cycle(cycle.id, [user_word])
    assert len(cycle_words) == 1
    assert cycle_words[0].cycle_id == cycle.id
    assert cycle_words[0].user_word_id == user_word.id
    assert cycle_words[0].is_learned is False
    assert cycle_words[0].time_spent == 0.0


def test_mark_word_as_learned(
    learning_service: LearningService, user: User, user_word: UserWord
) -> None:
    """Test marking a word as learned."""
    # Create a new cycle and add word to it
    cycle = learning_service.create_new_cycle(user.id)
    cycle_words = learning_service.add_words_to_cycle(cycle.id, [user_word])
    cycle_word = cycle_words[0]

    # Mark word as learned
    time_spent = 2.5
    learning_service.mark_word_as_learned(cycle.id, user_word.id, time_spent)

    # Refresh objects from database
    db.refresh(cycle_word)
    db.refresh(cycle)
    db.refresh(user_word)

    # Check cycle word status
    assert cycle_word.is_learned is True
    assert cycle_word.time_spent == time_spent

    # Check cycle statistics
    assert cycle.words_learned == 1
    assert cycle.time_spent == time_spent

    # Check user word status
    assert user_word.last_reviewed is not None
    assert user_word.review_stage == 1
    assert user_word.next_review > datetime.utcnow()


def test_complete_cycle(
    learning_service: LearningService, user: User, user_word: UserWord
) -> None:
    """Test completing a cycle."""
    # Create a new cycle
    cycle = learning_service.create_new_cycle(user.id)
    
    # Complete the cycle
    learning_service.complete_cycle(cycle.id)
    
    # Refresh cycle from database
    db.refresh(cycle)
    
    # Check cycle status
    assert cycle.is_completed is True
    assert cycle.end_time is not None


def test_log_user_activity(
    learning_service: LearningService, user: User
) -> None:
    """Test logging user activity."""
    message = "Test activity"
    level = "INFO"
    category = "test"
    
    learning_service.log_user_activity(user.id, message, level, category)
    
    # Check log entry
    log = (
        db.query(UserLog)
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