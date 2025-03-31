"""Learning service for managing learning cycles and word selection."""
import logging
import random
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Tuple
import math

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from collections import defaultdict

from enbot.config import settings
from enbot.models.models import (
    CycleWord,
    LearningCycle,
    User,
    UserLog,
    UserWord,
    Word,
)

logger = logging.getLogger(__name__)

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
        """Create a new learning cycle for the user and choose words for it."""

        words = self.choose_words_for_cycle(user_id, settings.learning.words_per_cycle)
        if not words: return None

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

        self.add_words_to_cycle(cycle.id, words)

        return cycle

    def _choose_words_with_priority(self, words: List[UserWord], num_words: int) -> List[UserWord]:
        """Choose words for a new learning cycle with priority."""
        priorities = defaultdict(int)
        prio_words = defaultdict(list)
        for word in words:
            priorities[word.priority] += 1
            prio_words[word.priority].append(word)
        chosen_words = []
        for priority in sorted(priorities.keys(), reverse=True):
            if priorities[priority] > 0:
                chosen_words.extend(prio_words[priority])
            if len(chosen_words) >= num_words: break
        return random.sample(chosen_words, min(len(chosen_words), num_words))

    def choose_words_for_cycle(self, user_id: int, words_per_cycle: int) -> List[UserWord]:
        """Choose words for a new learning cycle."""
        logger.info(f"Choosing words for cycle for user {user_id}")
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user: raise ValueError(f"User {user_id} not found")

        # Get words for review (already learned words)
        review_words = (
            self.db.query(Word)
            .join(UserWord)
            .filter(
                UserWord.user_id == user_id,
                UserWord.is_learned == True,
                UserWord.priority > 0,
                UserWord.next_review <= datetime.now(UTC)
            )
            .order_by(UserWord.priority.desc())
            .all()
        )
        logger.info(f"Review words: {len(review_words)}")
        review_words = self._choose_words_with_priority(review_words, math.ceil(words_per_cycle * settings.learning.new_words_ratio))
        logger.info(f"Review words after priority: {review_words}")
        # Calculate number of each prioritys
        new_words_to_take = words_per_cycle - len(review_words)
        new_words = (
            self.db.query(UserWord)
            .filter(
                UserWord.user_id == user_id,
                UserWord.is_learned == False,
            )
            .order_by(UserWord.priority.desc())
            .all()
        )
        logger.info(f"New words: {len(new_words)}")
        new_words = self._choose_words_with_priority(new_words, new_words_to_take)
        logger.info(f"New words after priority: {new_words}")
        words = review_words + new_words
        logger.info(f"Words: {words}")
        words = random.sample(words, min(len(words), words_per_cycle))
        logger.info(f"Words after sample: {words}")
        return words

    def get_words_for_cycle(self, user_id: int) -> List[UserWord]:
        """Get words for a new learning cycle."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user: raise ValueError(f"User {user_id} not found")

        # Get the active cycle
        cycle_words = []
        while True:
            # Get words for learning
            cycle = self.get_active_cycle(user_id)
            if not cycle: return []

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
            if cycle_words: break
            else: self.complete_cycle(cycle.id)

        return cycle_words
    
    def get_words_for_cycle_or_create(self, user_id: int) -> List[UserWord]:
        """Get the active cycle or create a new one if it doesn't exist."""
        cycle = self.get_active_cycle(user_id)
        if not cycle:
            cycle = self.create_new_cycle(user_id)
        words = self.get_words_for_cycle(user_id)
        if not words: self.complete_cycle(cycle.id)
        return words

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