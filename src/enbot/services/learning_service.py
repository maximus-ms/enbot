"""Learning service for managing learning cycles and word selection."""
import random
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from enbot.config import settings
from enbot.models.models import (
    CycleWord,
    LearningCycle,
    User,
    UserLog,
    UserWord,
    Word,
)


class LearningService:
    """Service for managing learning cycles and word selection."""

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db

    def get_active_cycle(self, user_id: int) -> Optional[LearningCycle]:
        """Get the user's active learning cycle."""
        return (
            self.db.query(LearningCycle)
            .filter(
                and_(
                    LearningCycle.user_id == user_id,
                    LearningCycle.is_completed == False,
                )
            )
            .first()
        )

    def create_new_cycle(self, user_id: int) -> LearningCycle:
        """Create a new learning cycle for the user."""
        cycle = LearningCycle(
            user_id=user_id,
            start_time=datetime.now(UTC),
            is_completed=False,
            words_learned=0,
            time_spent=0.0,
        )
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle

    def get_words_for_cycle(self, user_id: int, cycle_size: int) -> List[UserWord]:
        """Get words for a new learning cycle."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get the active cycle
        cycle = self.get_active_cycle(user_id)
        if not cycle:
            raise ValueError("No active cycle found")

        # Get words that are in the current cycle and not yet learned
        cycle_words = (
            self.db.query(UserWord)
            .join(CycleWord, UserWord.id == CycleWord.user_word_id)
            .filter(
                and_(
                    CycleWord.cycle_id == cycle.id,
                    CycleWord.is_learned == False,
                )
            )
            .all()
        )

        return cycle_words

    def add_words_to_cycle(
        self, cycle_id: int, user_words: List[UserWord]
    ) -> List[CycleWord]:
        """Add words to a learning cycle."""
        cycle_words = []
        for user_word in user_words:
            cycle_word = CycleWord(
                cycle_id=cycle_id,
                user_word_id=user_word.id,
                is_learned=False,
                time_spent=0.0,
            )
            cycle_words.append(cycle_word)
        self.db.add_all(cycle_words)
        self.db.commit()
        return cycle_words

    def mark_word_as_learned(
        self, cycle_id: int, user_word_id: int, time_spent: float
    ) -> None:
        """Mark a word as learned in the current cycle."""
        cycle_word = (
            self.db.query(CycleWord)
            .filter(
                and_(
                    CycleWord.cycle_id == cycle_id,
                    CycleWord.user_word_id == user_word_id,
                )
            )
            .first()
        )
        if not cycle_word:
            raise ValueError(f"Word {user_word_id} not found in cycle {cycle_id}")

        # Update cycle word status
        was_learned = cycle_word.is_learned
        cycle_word.is_learned = True
        cycle_word.time_spent += time_spent  # Accumulate time spent

        # Update cycle statistics
        cycle = cycle_word.cycle
        if not was_learned:  # Only increment words_learned if it wasn't already learned
            cycle.words_learned += 1
        cycle.time_spent += time_spent  # Accumulate time spent

        # Update user word status
        user_word = cycle_word.user_word
        user_word.last_reviewed = datetime.now(UTC)
        user_word.review_stage += 1
        user_word.next_review = self._calculate_next_review(user_word.review_stage)

        self.db.commit()

    def _calculate_next_review(self, review_stage: int) -> datetime:
        """Calculate the next review date based on the review stage."""
        if review_stage >= len(settings.learning.repetition_intervals):
            review_stage = len(settings.learning.repetition_intervals) - 1
        days = settings.learning.repetition_intervals[review_stage]
        next_review = datetime.now(UTC) + timedelta(days=days)
        return next_review.replace(tzinfo=UTC)  # Ensure timezone awareness

    def complete_cycle(self, cycle_id: int) -> None:
        """Mark a learning cycle as completed."""
        cycle = (
            self.db.query(LearningCycle)
            .filter(LearningCycle.id == cycle_id)
            .first()
        )
        if not cycle:
            raise ValueError(f"Cycle {cycle_id} not found")

        cycle.is_completed = True
        cycle.end_time = datetime.now(UTC)
        self.db.commit()

    def log_user_activity(
        self, user_id: int, message: str, level: str, category: str
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