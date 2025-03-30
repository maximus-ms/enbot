"""Tests for word service."""
from datetime import datetime, timedelta, UTC
from typing import Generator
from unittest.mock import Mock, patch
import os

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from enbot.models.base import SessionLocal, init_db, engine
from enbot.models.models import User, Word, UserWord
from enbot.services.word_service import WordService
from enbot.config import settings

fake = Faker()


@pytest.fixture(autouse=True)
def setup_database():
    """Delete and recreate the database before each test."""
    # Close any existing connections
    engine.dispose()
    
    # Delete the database file if it exists
    db_path = settings.database.url.replace('sqlite:///', '')
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create new database
    init_db()
    
    yield
    
    # Cleanup after test
    engine.dispose()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def word_service(db: Session) -> WordService:
    """Create a word service instance."""
    return WordService(db)


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


@pytest.fixture
def test_word(db: Session) -> Word:
    """Create a test word."""
    word = Word(
        text="test",
        translation="тест",
        transcription="test",
        pronunciation_file="test.mp3",
        image_file="test.jpg",
        language_pair="en-uk"
    )
    db.add(word)
    db.commit()
    return word


@pytest.fixture
def mock_user(db):
    user = User(
        telegram_id=123456789,
        username=fake.user_name(),
        target_language="en",
        native_language="ru"
    )
    db.add(user)
    db.commit()
    return user


def test_get_word(word_service: WordService, test_word: Word) -> None:
    """Test getting a word by ID."""
    word = word_service.get_word(test_word.id)
    assert word is not None
    assert word.id == test_word.id
    assert word.text == test_word.text


def test_get_word_by_text(word_service, db):
    # Create a test word
    word = Word(
        text="test",
        translation="тест",
        language_pair="en-ru"
    )
    db.add(word)
    db.commit()

    # Test getting the word
    result = word_service.get_word_by_text("TEST")
    assert result is not None
    assert result.text == "test"
    assert result.translation == "тест"


def test_create_word(word_service, mock_user, db, mocker):
    # Mock the content generator
    mock_word = Word(
        text="test",
        translation="тест",
        language_pair=f"{mock_user.native_language}-{mock_user.target_language}"
    )
    mock_generate = mocker.patch.object(
        word_service.content_generator,
        "generate_word_content",
        return_value=(mock_word, None)
    )

    # Create a word
    result = word_service.create_word("test", mock_user.telegram_id)

    # Verify the mock was called
    mock_generate.assert_called_once_with(
        "test",
        target_lang=mock_user.target_language,
        native_lang=mock_user.native_language
    )

    # Verify the word was created
    assert result.text == "test"
    assert result.translation == "тест"

    # Verify user-word association
    user_word = db.query(UserWord).filter(
        UserWord.user_id == mock_user.id,
        UserWord.word_id == result.id
    ).first()
    assert user_word is not None


def test_create_words(word_service, mock_user, db, mocker):
    # Mock the content generator
    mock_words = [
        Word(
            text="test1",
            translation="тест1",
            language_pair=f"{mock_user.native_language}-{mock_user.target_language}"
        ),
        Word(
            text="test2",
            translation="тест2",
            language_pair=f"{mock_user.native_language}-{mock_user.target_language}"
        )
    ]
    mock_generate = mocker.patch.object(
        word_service.content_generator,
        "generate_word_content",
        side_effect=[(w, None) for w in mock_words]
    )

    # Create words
    results = word_service.create_words(["test1", "test2"], mock_user.telegram_id)

    # Verify the mock was called twice
    assert mock_generate.call_count == 2

    # Verify words were created
    assert len(results) == 2
    assert results[0].text == "test1"
    assert results[1].text == "test2"

    # Verify user-word associations
    user_words = db.query(UserWord).filter(
        UserWord.user_id == mock_user.id
    ).all()
    assert len(user_words) == 2


def test_update_word(word_service: WordService, test_word: Word) -> None:
    """Test updating a word."""
    # Update word
    updated_word = word_service.update_word(
        test_word.id,
        translation="новый тест",
        transcription="new test"
    )
    
    # Check word was updated
    assert updated_word is not None
    assert updated_word.id == test_word.id
    assert updated_word.translation == "новый тест"
    assert updated_word.transcription == "new test"


def test_delete_word(word_service: WordService, test_word: Word) -> None:
    """Test deleting a word."""
    # Mock content generator
    word_service.content_generator.delete_file = Mock()
    
    # Delete word
    word_service.delete_word(test_word.id)
    
    # Check word was deleted
    deleted_word = word_service.db.query(Word).filter(
        Word.id == test_word.id
    ).first()
    assert deleted_word is None
    
    # Check files were deleted
    word_service.content_generator.delete_file.assert_any_call(test_word.pronunciation_file)
    word_service.content_generator.delete_file.assert_any_call(test_word.image_file)


def test_get_user_words(word_service: WordService, test_user: User, test_word: Word) -> None:
    """Test getting words associated with a user."""
    # Create user word association
    user_word = UserWord(
        user_id=test_user.id,
        word_id=test_word.id,
        is_learned=True,
        priority=1
    )
    word_service.db.add(user_word)
    word_service.db.commit()
    
    # Get all words
    words = word_service.get_user_words(test_user.id)
    assert len(words) == 1
    assert words[0].id == test_word.id
    
    # Get learned words
    learned_words = word_service.get_user_words(test_user.id, learned=True)
    assert len(learned_words) == 1
    
    # Get unlearned words
    unlearned_words = word_service.get_user_words(test_user.id, learned=False)
    assert len(unlearned_words) == 0
    
    # Get words with priority
    priority_words = word_service.get_user_words(test_user.id, priority=1)
    assert len(priority_words) == 1
    
    # Get words with limit
    limited_words = word_service.get_user_words(test_user.id, limit=1)
    assert len(limited_words) == 1


def test_get_user_word_count(word_service: WordService, test_user: User, test_word: Word) -> None:
    """Test getting the count of words associated with a user."""
    # Create user word association
    user_word = UserWord(
        user_id=test_user.id,
        word_id=test_word.id,
        is_learned=True
    )
    word_service.db.add(user_word)
    word_service.db.commit()
    
    # Get total count
    total_count = word_service.get_user_word_count(test_user.id)
    assert total_count == 1
    
    # Get learned count
    learned_count = word_service.get_user_word_count(test_user.id, learned=True)
    assert learned_count == 1
    
    # Get unlearned count
    unlearned_count = word_service.get_user_word_count(test_user.id, learned=False)
    assert unlearned_count == 0


def test_search_words(word_service: WordService, test_word: Word) -> None:
    """Test searching for words."""
    # Create more test words
    for i in range(10):
        word = Word(
            text=f"test{i}",
            translation=f"тест{i}",
            language_pair="en-uk"
        )
        word_service.db.add(word)
    word_service.db.commit()
    
    # Search for words
    words = word_service.search_words("test")
    
    # Check results
    assert len(words) == 10  # Default limit is 10
    assert all("test" in word.text.lower() for word in words)


def test_get_word_details(word_service: WordService, test_user: User, test_word: Word) -> None:
    """Test getting detailed information about a word."""
    # Create user word association
    user_word = UserWord(
        user_id=test_user.id,
        word_id=test_word.id,
        is_learned=True,
        priority=1,
        review_stage=1,
        next_review=datetime.now(UTC) + timedelta(days=1)
    )
    word_service.db.add(user_word)
    word_service.db.commit()
    
    # Get word details
    details = word_service.get_word_details(test_word.id, test_user.id)
    
    # Check details
    assert details is not None
    assert details["id"] == test_word.id
    assert details["text"] == test_word.text
    assert details["translation"] == test_word.translation
    assert details["transcription"] == test_word.transcription
    assert details["pronunciation_file"] == test_word.pronunciation_file
    assert details["image_file"] == test_word.image_file
    assert details["priority"] == user_word.priority
    assert details["is_learned"] == user_word.is_learned
    assert details["review_stage"] == user_word.review_stage
    assert details["next_review"] == user_word.next_review
    assert details["created_at"] == test_word.created_at
    assert details["updated_at"] == test_word.updated_at


def test_get_random_words(word_service: WordService, test_user: User, test_word: Word) -> None:
    """Test getting random words."""
    # Create user word association
    user_word = UserWord(
        user_id=test_user.id,
        word_id=test_word.id,
        is_learned=True
    )
    word_service.db.add(user_word)
    word_service.db.commit()
    
    # Get random words
    random_words = word_service.get_random_words(test_user.id, count=1)
    assert len(random_words) == 1
    assert random_words[0].id == test_word.id
    
    # Get random learned words
    learned_words = word_service.get_random_words(test_user.id, count=1, learned=True)
    assert len(learned_words) == 1
    assert learned_words[0].id == test_word.id
    
    # Get random unlearned words
    unlearned_words = word_service.get_random_words(test_user.id, count=1, learned=False)
    assert len(unlearned_words) == 0


def test_get_words_for_review(word_service: WordService, test_user: User, test_word: Word) -> None:
    """Test getting words for review."""
    # Create user word association with next review in the past
    user_word = UserWord(
        user_id=test_user.id,
        word_id=test_word.id,
        is_learned=True,
        next_review=datetime.now(UTC) - timedelta(days=1)
    )
    word_service.db.add(user_word)
    word_service.db.commit()
    
    # Get words for review
    review_words = word_service.get_words_for_review(test_user.id)
    assert len(review_words) == 1
    assert review_words[0].id == test_word.id
    
    # Get words for review with limit
    limited_review_words = word_service.get_words_for_review(test_user.id, count=1)
    assert len(limited_review_words) == 1


if __name__ == "__main__":
    pytest.main([__file__]) 