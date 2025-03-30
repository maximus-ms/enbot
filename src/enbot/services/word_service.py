"""Service for managing words in the system."""
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from enbot.models.models import Word, UserWord, User
from enbot.services.content_generator import ContentGenerator


class WordService:
    """Service for managing words in the system."""

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db
        self.content_generator = ContentGenerator()

    def get_word(self, word_id: int) -> Optional[Word]:
        """Get a word by its ID."""
        return self.db.query(Word).filter(Word.id == word_id).first()

    def get_word_by_text(self, text: str) -> Optional[Word]:
        """Get a word by its text."""
        return self.db.query(Word).filter(Word.text.ilike(text)).first()

    def create_word(self, text: str, user_id: int, priority: int = 0) -> Word:
        """Create a new word and generate its content."""
        # Get user settings
        user = self.db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Check if word already exists
        existing_word = self.get_word_by_text(text)
        if existing_word:
            # Create user word association if it doesn't exist
            user_word = self.db.query(UserWord).filter(
                UserWord.user_id == user.id,
                UserWord.word_id == existing_word.id
            ).first()
            if not user_word:
                user_word = UserWord(
                    user_id=user.id,
                    word_id=existing_word.id,
                    priority=priority,
                )
                self.db.add(user_word)
                self.db.commit()
            return existing_word

        # Generate word content
        word_obj, _ = self.content_generator.generate_word_content(
            text,
            target_lang=user.target_language,
            native_lang=user.native_language
        )
        
        # Create word
        self.db.add(word_obj)
        self.db.commit()
        self.db.refresh(word_obj)

        # Create user word association
        user_word = UserWord(
            user_id=user.id,
            word_id=word_obj.id,
            priority=priority,
        )
        self.db.add(user_word)
        self.db.commit()

        return word_obj

    def create_words(self, texts: List[str], user_id: int, priority: int = 0) -> List[Word]:
        """Create multiple words at once."""
        # Get user settings
        user = self.db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            raise ValueError("User not found")

        words = []
        for text in texts:
            # Check if word already exists
            existing_word = self.get_word_by_text(text)
            if existing_word:
                # Create user word association if it doesn't exist
                user_word = self.db.query(UserWord).filter(
                    UserWord.user_id == user.id,
                    UserWord.word_id == existing_word.id
                ).first()
                if not user_word:
                    user_word = UserWord(
                        user_id=user.id,
                        word_id=existing_word.id,
                        priority=priority,
                    )
                    self.db.add(user_word)
                    self.db.commit()
                words.append(existing_word)
                continue

            # Generate word content
            word_obj, _ = self.content_generator.generate_word_content(
                text,
                target_lang=user.target_language,
                native_lang=user.native_language
            )
            
            # Create word
            self.db.add(word_obj)
            self.db.commit()
            self.db.refresh(word_obj)

            # Create user word association
            user_word = UserWord(
                user_id=user.id,
                word_id=word_obj.id,
                priority=priority,
            )
            self.db.add(user_word)
            self.db.commit()

            words.append(word_obj)

        return words

    def update_word(self, word_id: int, **kwargs) -> Optional[Word]:
        """Update a word's attributes."""
        word = self.get_word(word_id)
        if not word:
            return None

        for key, value in kwargs.items():
            if hasattr(word, key):
                setattr(word, key, value)

        self.db.commit()
        self.db.refresh(word)
        return word

    def delete_word(self, word_id: int) -> bool:
        """Delete a word and its associated content."""
        word = self.get_word(word_id)
        if not word:
            return False

        # Delete associated files
        if word.pronunciation_file:
            self.content_generator.delete_file(word.pronunciation_file)
        if word.image_file:
            self.content_generator.delete_file(word.image_file)

        # Delete word
        self.db.delete(word)
        self.db.commit()
        return True

    def get_word_count(self) -> int:
        """Get the count of words in the database."""
        return self.db.query(Word).count()

    def get_user_words(
        self,
        user_id: int,
        learned: Optional[bool] = None,
        priority: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Word]:
        """Get words associated with a user."""
        query = (
            self.db.query(Word)
            .join(UserWord)
            .filter(UserWord.user_id == user_id)
        )

        if learned is not None:
            query = query.filter(UserWord.is_learned == learned)
        if priority is not None:
            query = query.filter(UserWord.priority == priority)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_user_word_count(self, user_id: int, learned: Optional[bool] = None) -> int:
        """Get the count of words associated with a user."""
        query = (
            self.db.query(UserWord)
            .filter(UserWord.user_id == user_id)
        )

        if learned is not None:
            query = query.filter(UserWord.is_learned == learned)

        return query.count()

    def search_words(
        self,
        query: str,
        user_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Word]:
        """Search for words by text or translation."""
        search_query = (
            self.db.query(Word)
            .filter(
                or_(
                    Word.text.ilike(f"%{query}%"),
                    Word.translation.ilike(f"%{query}%"),
                )
            )
        )

        if user_id:
            search_query = search_query.join(UserWord).filter(UserWord.user_id == user_id)

        return search_query.limit(limit).all()

    def get_word_details(self, word_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a word."""
        word = self.get_word(word_id)
        if not word:
            return None

        user_word = (
            self.db.query(UserWord)
            .filter(
                and_(
                    UserWord.word_id == word_id,
                    UserWord.user_id == user_id,
                )
            )
            .first()
        )

        if not user_word:
            return None

        return {
            "id": word.id,
            "text": word.text,
            "translation": word.translation,
            "transcription": word.transcription,
            "pronunciation_file": word.pronunciation_file,
            "image_file": word.image_file,
            "priority": user_word.priority,
            "is_learned": user_word.is_learned,
            "review_stage": user_word.review_stage,
            "next_review": user_word.next_review,
            "created_at": word.created_at,
            "updated_at": word.updated_at,
        }

    def get_random_words(
        self,
        user_id: int,
        count: int = 10,
        learned: Optional[bool] = None,
    ) -> List[Word]:
        """Get random words for a user."""
        query = (
            self.db.query(Word)
            .join(UserWord)
            .filter(UserWord.user_id == user_id)
        )

        if learned is not None:
            query = query.filter(UserWord.is_learned == learned)

        return query.order_by(func.random()).limit(count).all()

    def get_words_for_review(
        self,
        user_id: int,
        count: int = 10,
    ) -> List[Word]:
        """Get words that are due for review."""
        return (
            self.db.query(Word)
            .join(UserWord)
            .filter(
                and_(
                    UserWord.user_id == user_id,
                    UserWord.is_learned == True,
                    UserWord.next_review <= datetime.now(UTC),
                )
            )
            .order_by(UserWord.next_review)
            .limit(count)
            .all()
        ) 