"""Service for managing user notifications."""
from datetime import datetime, timedelta, UTC
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from enbot.models.models import User, UserWord, LearningCycle
from enbot.services.word_service import WordService
from enbot.config import settings


class NotificationService:
    """Service for managing user notifications."""

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db
        self.word_service = WordService(db)

    def get_users_for_notification(self) -> List[User]:
        """Get users who should receive notifications."""
        current_hour = datetime.now(UTC).hour
        
        return (
            self.db.query(User)
            .filter(
                and_(
                    User.notifications_enabled == True,
                    User.notification_hour == current_hour,
                )
            )
            .all()
        )

    def get_all_users_for_notification(self) -> List[User]:
        """Get all users who should receive notifications"""
        
        return (
            self.db.query(User)
            .filter(
                and_(
                    User.notifications_enabled == True,
                )
            )
            .all()
        )

    def get_daily_reminder_message(self, user: User) -> str:
        """Generate a daily reminder message for a user."""
        # Get user's statistics
        total_words = self.word_service.get_user_word_count(user.id)
        learned_words = self.word_service.get_user_word_count(user.id, learned=True)
        words_for_review = self.word_service.get_words_for_review(user.id)
        
        # Calculate progress
        progress = (learned_words / total_words * 100) if total_words > 0 else 0
        
        # Get active cycle
        active_cycle = (
            self.db.query(LearningCycle)
            .filter(
                and_(
                    LearningCycle.user_id == user.id,
                    LearningCycle.is_completed == False,
                )
            )
            .first()
        )
        
        message = (
            f"🌅 Good morning, {user.username}!\n\n"
            f"📊 Your Learning Progress:\n"
            f"• Total Words: {total_words}\n"
            f"• Learned Words: {learned_words}\n"
            f"• Progress: {progress:.1f}%\n"
            f"• Words for Review: {len(words_for_review)}\n\n"
        )
        
        if active_cycle:
            message += (
                f"🎯 Today's Goals:\n"
                f"• Words to Learn: {active_cycle.words_learned}/{user.daily_goal_words}\n"
                f"• Time Spent: {active_cycle.time_spent:.1f}/{user.daily_goal_minutes} minutes\n\n"
            )
        
        message += (
            "💡 Ready to learn some new words?\n"
            "Use /start to begin your learning session!"
        )
        
        return message

    def get_review_reminder_message(self, user: User) -> str:
        """Generate a review reminder message for a user."""
        words_for_review = self.word_service.get_words_for_review(user.id)
        
        if not words_for_review:
            return None
        
        message = (
            f"⏰ Time for Review!\n\n"
            f"You have {len(words_for_review)} words to review:\n"
        )
        
        # Add first 5 words as examples
        for word in words_for_review[:5]:
            message += f"• {word.text}\n"
        
        if len(words_for_review) > 5:
            message += f"... and {len(words_for_review) - 5} more\n"
        
        message += "\nUse /start to begin your review session!"
        
        return message

    def get_achievement_message(self, user: User) -> Optional[str]:
        """Generate an achievement message for a user."""
        # Get user's statistics
        total_words = self.word_service.get_user_word_count(user.id)
        learned_words = self.word_service.get_user_word_count(user.id, learned=True)
        
        # Check for achievements
        if learned_words == 10:
            return (
                "🎉 Achievement Unlocked!\n\n"
                "You've learned your first 10 words!\n"
                "Keep up the great work! 🌟"
            )
        elif learned_words == 50:
            return (
                "🏆 Achievement Unlocked!\n\n"
                "You've learned 50 words!\n"
                "You're making amazing progress! 🌟"
            )
        elif learned_words == 100:
            return (
                "🌟 Achievement Unlocked!\n\n"
                "You've learned 100 words!\n"
                "You're becoming a vocabulary master! 🌟"
            )
        elif learned_words == 500:
            return (
                "👑 Achievement Unlocked!\n\n"
                "You've learned 500 words!\n"
                "You're absolutely incredible! 🌟"
            )
        
        return None

    def get_streak_message(self, user: User) -> Optional[str]:
        """Generate a streak message for a user."""
        # Get user's learning cycles for the last 7 days
        cycles = (
            self.db.query(LearningCycle)
            .filter(
                and_(
                    LearningCycle.user_id == user.id,
                    LearningCycle.is_completed == True,
                    LearningCycle.end_time >= datetime.now(UTC) - timedelta(days=7),
                )
            )
            .all()
        )
        
        streak = len(cycles)
        
        if streak == 7:
            return (
                "🔥 Amazing Streak!\n\n"
                "You've completed your learning sessions for 7 days in a row!\n"
                "You're on fire! Keep it up! 🌟"
            )
        elif streak == 30:
            return (
                "🌟 Legendary Streak!\n\n"
                "You've completed your learning sessions for 30 days in a row!\n"
                "You're absolutely incredible! 🌟"
            )
        
        return None

    def should_send_review_reminder(self, user: User) -> bool:
        """Check if a review reminder should be sent to the user."""
        if not user.notifications_enabled:
            return False
        
        # Get words for review
        words_for_review = self.word_service.get_words_for_review(user.id)
        if not words_for_review:
            return False
        
        # Check if user has an active cycle
        active_cycle = (
            self.db.query(LearningCycle)
            .filter(
                and_(
                    LearningCycle.user_id == user.id,
                    LearningCycle.is_completed == False,
                )
            )
            .first()
        )
        
        # Don't send reminder if user is actively learning
        if active_cycle:
            return False
        
        # Check last notification time
        last_notification = user.last_notification_time
        if last_notification:
            # Don't send more than one reminder per day
            if last_notification.date() == datetime.now(UTC).date():
                return False
        
        return True

    def update_last_notification_time(self, user: User) -> None:
        """Update the user's last notification time."""
        user.last_notification_time = datetime.now(UTC)
        self.db.commit() 