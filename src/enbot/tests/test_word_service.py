"""Tests for word service."""
from datetime import datetime, timedelta
from typing import Generator

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from enbot.models.base import SessionLocal, init_db
from enbot.models.models import User, Word, UserWord
from enbot.services.word_service import WordService

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
def word_service(db: Session) -> WordService:
    """Create a word service instance."""
    return WordService(db)


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        telegram_id=fake.random_int(),
        username=fake.user_name(),
    )
    db.add(user)
    db.commit()
    return user


def test_get_word(word_service: WordService, test_user: User) -> None:
    """Test getting a word by ID."""
    # Create a test word
    word = Word(text="test")
    word_service.db.add(word)
    word_service.db.commit()
    
    # Get word
    retrieved_word = word_service.get_word(word.id)
    assert retrieved_word is not None
    assert retrieved_word.text == "test"


def test_get_word_by_text(word_service: WordService, test_user: User) -> None:
    """Test getting a word by text."""
    # Create a test word
    word = Word(text="test")
    word_service.db.add(word)
    word_service.db.commit()
    
    # Get word
    retrieved_word = word_service.get_word_by_text("test")
    assert retrieved_word is not None
    assert retrieved_word.id == word.id


def test_create_word(word_service: WordService, test_user: User) -> None:
    """Test creating a new word."""
    # Create word
    word = word_service.create_word("hello", test_user.id)
    
    # Check word
    assert word.text == "hello"
    assert word.translation is not None
    assert word.transcription is not None
    assert word.pronunciation_file is not None
    assert word.image_file is not None
    
    # Check user word association
    user_word = (
        word_service.db.query(UserWord)
        .filter(
            UserWord.user_id == test_user.id,
            UserWord.word_id == word.id,
        )
        .first()
    )
    assert user_word is not None
    assert user_word.priority == 5


def test_create_words(word_service: WordService, test_user: User) -> None:
    """Test creating multiple words."""
    # Create words
    words = word_service.create_words(["hello", "world", "python"], test_user.id)
    
    # Check words
    assert len(words) == 3
    for word in words:
        assert word.text in ["hello", "world", "python"]
        assert word.translation is not None
        assert word.transcription is not None
    
    # Check user word associations
    user_words = (
        word_service.db.query(UserWord)
        .filter(UserWord.user_id == test_user.id)
        .all()
    )
    assert len(user_words) == 3


def test_update_word(word_service: WordService, test_user: User) -> None:
    """Test updating a word."""
    # Create word
    word = word_service.create_word("hello", test_user.id)
    
    # Update word
    updated_word = word_service.update_word(
        word.id,
        translation="new translation",
        priority=7,
    )
    
    # Check updates
    assert updated_word is not None
    assert updated_word.translation == "new translation"
    
    # Check user word priority
    user_word = (
        word_service.db.query(UserWord)
        .filter(
            UserWord.user_id == test_user.id,
            UserWord.word_id == word.id,
        )
        .first()
    )
    assert user_word.priority == 7


def test_delete_word(word_service: WordService, test_user: User) -> None:
    """Test deleting a word."""
    # Create word
    word = word_service.create_word("hello", test_user.id)
    
    # Delete word
    success = word_service.delete_word(word.id)
    assert success is True
    
    # Check word is deleted
    deleted_word = word_service.get_word(word.id)
    assert deleted_word is None
    
    # Check user word association is deleted
    user_word = (
        word_service.db.query(UserWord)
        .filter(
            UserWord.user_id == test_user.id,
            UserWord.word_id == word.id,
        )
        .first()
    )
    assert user_word is None


def test_get_user_words(word_service: WordService, test_user: User) -> None:
    """Test getting user's words."""
    # Create words
    word_service.create_words(["hello", "world", "python"], test_user.id)
    
    # Get all words
    words = word_service.get_user_words(test_user.id)
    assert len(words) == 3
    
    # Get learned words
    learned_words = word_service.get_user_words(test_user.id, learned=True)
    assert len(learned_words) == 0
    
    # Get words with priority
    priority_words = word_service.get_user_words(test_user.id, priority=5)
    assert len(priority_words) == 3


def test_get_user_word_count(word_service: WordService, test_user: User) -> None:
    """Test getting user's word count."""
    # Create words
    word_service.create_words(["hello", "world", "python"], test_user.id)
    
    # Get total count
    total_count = word_service.get_user_word_count(test_user.id)
    assert total_count == 3
    
    # Get learned count
    learned_count = word_service.get_user_word_count(test_user.id, learned=True)
    assert learned_count == 0


def test_search_words(word_service: WordService, test_user: User) -> None:
    """Test searching for words."""
    # Create words
    word_service.create_words(["hello", "world", "python"], test_user.id)
    
    # Search by text
    text_results = word_service.search_words("hello")
    assert len(text_results) == 1
    assert text_results[0].text == "hello"
    
    # Search by translation
    translation_results = word_service.search_words("привіт")
    assert len(translation_results) == 1
    assert translation_results[0].text == "hello"
    
    # Search with user filter
    user_results = word_service.search_words("hello", user_id=test_user.id)
    assert len(user_results) == 1


def test_get_word_details(word_service: WordService, test_user: User) -> None:
    """Test getting word details."""
    # Create word
    word = word_service.create_word("hello", test_user.id)
    
    # Get details
    details = word_service.get_word_details(word.id, test_user.id)
    assert details is not None
    assert details["text"] == "hello"
    assert details["translation"] is not None
    assert details["transcription"] is not None
    assert details["priority"] == 5
    assert details["is_learned"] is False
    assert details["review_stage"] == 0


def test_get_random_words(word_service: WordService, test_user: User) -> None:
    """Test getting random words."""
    # Create words
    word_service.create_words(["hello", "world", "python"], test_user.id)
    
    # Get random words
    random_words = word_service.get_random_words(test_user.id, count=2)
    assert len(random_words) == 2
    assert all(word.text in ["hello", "world", "python"] for word in random_words)


def test_get_words_for_review(word_service: WordService, test_user: User) -> None:
    """Test getting words for review."""
    # Create word
    word = word_service.create_word("hello", test_user.id)
    
    # Set next review time
    user_word = (
        word_service.db.query(UserWord)
        .filter(
            UserWord.user_id == test_user.id,
            UserWord.word_id == word.id,
        )
        .first()
    )
    user_word.next_review = datetime.utcnow() - timedelta(days=1)
    word_service.db.commit()
    
    # Get words for review
    review_words = word_service.get_words_for_review(test_user.id)
    assert len(review_words) == 1
    assert review_words[0].text == "hello"


if __name__ == "__main__":
    pytest.main([__file__]) 