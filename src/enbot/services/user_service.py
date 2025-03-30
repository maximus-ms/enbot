"""User service for managing user data and preferences."""
from datetime import datetime, timedelta, UTC
from typing import List, Optional
import logging

from sqlalchemy import and_
from sqlalchemy.orm import Session

from enbot.config import settings
from enbot.models.models import User, UserLog, UserWord, Word, LearningCycle
from enbot.services.content_generator import ContentGenerator

# Configure logging
logger = logging.getLogger(__name__)

class UserService:
    """Service for managing user data and preferences."""

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db
        self.content_generator = ContentGenerator()

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID."""
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()

    def get_user_words(self, user_id: int) -> List[UserWord]:
        """Get all unlearned words for a user."""
        words = (
            self.db.query(UserWord)
            .filter(
                and_(
                    UserWord.user_id == user_id,
                    UserWord.is_learned == False
                )
            )
            .all()
        )
        logger.info(f"Found {len(words)} unlearned words for user {user_id}")
        return words

    def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        native_language: str = "uk",
        target_language: str = "en",
    ) -> User:
        """Get existing user or create a new one."""
        user = (
            self.db.query(User)
            .filter(User.telegram_id == telegram_id)
            .first()
        )
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                native_language=native_language,
                target_language=target_language,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            self.log_user_activity(
                user.id,
                "User created",
                "INFO",
                "user_created",
            )
        
        return user

    def update_user_settings(
        self,
        user_id: int,
        native_language: Optional[str] = None,
        target_language: Optional[str] = None,
        daily_goal_minutes: Optional[int] = None,
        daily_goal_words: Optional[int] = None,
        day_start_hour: Optional[int] = None,
    ) -> User:
        """Update user settings."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        if native_language is not None:
            user.native_language = native_language
        if target_language is not None:
            user.target_language = target_language
        if daily_goal_minutes is not None:
            user.daily_goal_minutes = daily_goal_minutes
        if daily_goal_words is not None:
            user.daily_goal_words = daily_goal_words
        if day_start_hour is not None:
            user.day_start_hour = day_start_hour

        self.db.commit()
        self.db.refresh(user)
        
        self.log_user_activity(
            user.id,
            "User settings updated",
            "INFO",
            "settings_updated",
        )
        
        return user

    def add_words(
        self,
        user_id: int,
        words: List[str],
        priority: int = 0,
    ) -> List[UserWord]:
        """Add new words to user's dictionary."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        added_words = []
        for word_text in words:
            # Check if word already exists
            existing_word = (
                self.db.query(Word)
                .filter(
                    and_(
                        Word.text == word_text,
                        Word.language_pair == f"{user.target_language}-{user.native_language}",
                    )
                )
                .first()
            )

            if existing_word:
                # Check if user already has this word
                existing_user_word = (
                    self.db.query(UserWord)
                    .filter(
                        and_(
                            UserWord.user_id == user_id,
                            UserWord.word_id == existing_word.id,
                        )
                    )
                    .first()
                )

                if existing_user_word:
                    # Update priority if higher
                    if priority > existing_user_word.priority:
                        existing_user_word.priority = priority
                        self.log_user_activity(
                            user_id,
                            f"Word priority updated: {word_text}",
                            "INFO",
                            "word_priority_updated",
                        )
                        added_words.append(existing_user_word)
                    continue

                user_word = UserWord(
                    user_id=user_id,
                    word_id=existing_word.id,
                    priority=priority,
                    is_learned=False,
                    last_reviewed=None,
                    next_review=None,
                    review_stage=0,
                )
            else:
                # Generate content for new word
                word_obj, examples = self.content_generator.generate_word_content(
                    word_text,
                    user.target_language,
                    user.native_language,
                )
                self.db.add(word_obj)
                self.db.commit()
                self.db.refresh(word_obj)

                # Add examples
                for example in examples:
                    example.word_id = word_obj.id
                    self.db.add(example)
                self.db.commit()

                user_word = UserWord(
                    user_id=user_id,
                    word_id=word_obj.id,
                    priority=priority,
                    is_learned=False,
                    last_reviewed=None,
                    next_review=None,
                    review_stage=0,
                )

            self.db.add(user_word)
            added_words.append(user_word)

        self.db.commit()
        self.log_user_activity(
            user_id,
            f"Added {len(added_words)} new words",
            "INFO",
            "words_added",
        )
        
        return added_words

    def get_user_statistics(
        self,
        user_id: int,
        days: int = 30,
    ) -> dict:
        """Get user learning statistics."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Calculate date range
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Get completed cycles in date range
        cycles = (
            self.db.query(LearningCycle)
            .filter(
                and_(
                    LearningCycle.user_id == user_id,
                    LearningCycle.is_completed == True,
                    LearningCycle.end_time >= start_date,
                    LearningCycle.end_time <= end_date,
                )
            )
            .all()
        )

        # Calculate statistics
        total_words = sum(cycle.words_learned for cycle in cycles)
        total_time = sum(cycle.time_spent for cycle in cycles)
        total_cycles = len(cycles)

        return {
            "total_words": total_words,
            "total_time_minutes": total_time,
            "total_cycles": total_cycles,
            "average_words_per_cycle": total_words / total_cycles if total_cycles > 0 else 0,
            "average_time_per_cycle": total_time / total_cycles if total_cycles > 0 else 0,
        }

    def log_user_activity(
        self,
        user_id: int,
        message: str,
        level: str,
        category: str,
    ) -> None:
        """Log user activity."""
        log = UserLog(
            user_id=user_id,
            message=message,
            level=level,
            category=category,
        )
        self.db.add(log)
        self.db.commit() 