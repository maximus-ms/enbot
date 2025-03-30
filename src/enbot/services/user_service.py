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

    def get_user_words(
        self,
        user_id: int,
        learned: Optional[bool] = None,
        priority: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[UserWord]:
        """Get all words for a user with optional filtering."""
        query = (
            self.db.query(UserWord)
            .filter(UserWord.user_id == user_id)
        )

        if learned is not None:
            query = query.filter(UserWord.is_learned == learned)
        if priority is not None:
            query = query.filter(UserWord.priority == priority)
        if limit is not None:
            query = query.limit(limit)

        return query.all()
    
    def get_non_user_words(self, user_id: int, limit: Optional[int] = None) -> List[str]:
        """Get all words that are not in the user's dictionary."""
        # Create a subquery to get word_ids that are in user's dictionary
        user_word_ids = (
            self.db.query(UserWord.word_id)
            .filter(UserWord.user_id == user_id)
            .subquery()
        )
        
        # Get all words that are not in the subquery
        query = (
            self.db.query(Word)
            .filter(~Word.id.in_(user_word_ids))
        )
        if limit is not None: query = query.limit(limit)
        return [word.text for word in query.all()]

    def get_user_word_count(self, user_id: int, learned: Optional[bool] = None) -> int:
        """Get the count of unlearned words for a user."""
        query = self.db.query(UserWord).filter(UserWord.user_id == user_id)
        if learned is not None: query = query.filter(UserWord.is_learned == learned)
        return query.count()

    def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        native_language: str = "uk",
        target_language: str = "en",
    ) -> User:
        """Get existing user or create a new one."""
        user = self.get_user_by_telegram_id(telegram_id)
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                native_language=native_language,
                target_language=target_language,
                day_start_hour=settings.learning.day_start_hour,
                notification_hour=self._time_to_hour(settings.notification.daily_reminder_time),
                is_admin=telegram_id in settings.bot.admin_ids,
                notifications_enabled=settings.notification.enabled,
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

    def _time_to_hour(self, time_str: str) -> int:
        """Convert time string (HH:MM) to hour integer"""
        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            return time_obj.hour
        except ValueError as e:
            raise ValueError(f"Invalid time format. Expected HH:MM, got {time_str}") from e

    def update_user_settings(
        self,
        user_id: int,
        native_language: Optional[str] = None,
        target_language: Optional[str] = None,
        daily_goal_minutes: Optional[int] = None,
        daily_goal_words: Optional[int] = None,
        day_start_hour: Optional[int] = None,
        notification_hour: Optional[int] = None,
        notifications_enabled: Optional[bool] = None,
        word_add_last_date: Optional[datetime] = None,
    ) -> User:
        """Update user settings."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        log_message = f"User settings updated: ["
        if native_language is not None:
            user.native_language = native_language
            log_message += f" native_language: {native_language},"
        if target_language is not None:
            user.target_language = target_language
            log_message += f" target_language: {target_language},"
        if daily_goal_minutes is not None:
            user.daily_goal_minutes = daily_goal_minutes
            log_message += f" daily_goal_minutes: {daily_goal_minutes},"
        if daily_goal_words is not None:
            user.daily_goal_words = daily_goal_words
            log_message += f" daily_goal_words: {daily_goal_words},"
        if day_start_hour is not None:
            user.day_start_hour = day_start_hour
            log_message += f" day_start_hour: {day_start_hour}"
        if notification_hour is not None:
            user.notification_hour = notification_hour
            log_message += f" notification_hour: {notification_hour}"
        if notifications_enabled is not None:
            user.notifications_enabled = notifications_enabled
            log_message += f" notifications_enabled: {notifications_enabled}"
        if word_add_last_date is not None:
            user.word_add_last_date = word_add_last_date
            log_message += f" word_add_last_date: {word_add_last_date}"
        log_message += "]"

        self.db.commit()
        self.db.refresh(user)
        
        self.log_user_activity(
            user.id,
            log_message,
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
        if len(words) == 0: return []
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user: raise ValueError(f"User {user_id} not found")

        # Check if user did not added words today, check if user has words with the same priority and if so, decrease the priority by 1
        if user.word_add_last_date is None or user.word_add_last_date.date() != datetime.now(UTC).date():
            all_user_words = self.get_user_words(user_id)
            # get list of all priorities
            priorities = sorted(set([word.priority for word in all_user_words]), reverse=True)

            # check if we need to decrease priority
            if priorities and priority == priorities[0]:
                # All conflictiong priorities must be decreased
                priorities_to_decrease = [priorities[0]]
                for _priority in priorities[1:]:
                    if _priority <= settings.learning.default_priority: break
                    if _priority+1 != priorities_to_decrease[-1]: break
                    priorities_to_decrease.append(_priority)

                for word in all_user_words:
                    if word.priority in priorities_to_decrease:
                        word.priority -= 1
                        self.db.add(word)

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
                        if priority > existing_user_word.priority+1:
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
            added_words.append(user_word)
            self.db.add(user_word)

        if len(added_words) > 0:
            user.word_add_last_date = datetime.now(UTC)
            self.db.add(user)

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
        
        total_user_words = self.get_user_word_count(user_id)

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
            "total_user_words": total_user_words,
        }

    def get_users_count(self) -> int:
        """Get the total number of users in the database."""
        return self.db.query(User).count()

    def log_user_activity(
        self,
        user_id: int,
        message: str,
        level: str,
        category: str,
    ) -> None:
        """Log user activity."""
        logger.log(logging.getLevelName(level), f"Logging user activity: {message}")
        log = UserLog(
            user_id=user_id,
            message=message,
            level=level,
            category=category,
        )
        self.db.add(log)
        self.db.commit() 