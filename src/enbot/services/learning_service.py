"""Learning service for managing learning cycles and word selection."""
import logging
import random
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Tuple
import math
import json

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
    UserCycle,
)
from enbot.models.cycle_models import WordProgressData

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

    def get_words_for_cycle(self, user_id: int) -> Tuple[List[UserWord], Optional[LearningCycle]]:
        """Get words for a new learning cycle."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user: raise ValueError(f"User {user_id} not found")

        # Get the active cycle
        cycle_words = []
        while True:
            # Get words for learning
            cycle = self.get_active_cycle(user_id)
            if not cycle: return [], None

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

        return cycle_words, cycle
    
    def get_words_for_cycle_or_create(self, user_id: int) -> Tuple[List[UserWord], LearningCycle]:
        """Get the active cycle or create a new one if it doesn't exist."""
        words, cycle = self.get_words_for_cycle(user_id)
        if not cycle:
            cycle = self.create_new_cycle(user_id)
            words, cycle = self.get_words_for_cycle(user_id)
        if not words and cycle:
            self.complete_cycle(cycle.id)
            cycle = None
        return words, cycle

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
        self, user_id: int, word_id: int, time_spent: float
    ) -> None:
        """Mark a word as learned in the current cycle."""

        learning_cycle = self.get_active_cycle(user_id)
        if not learning_cycle:
            raise ValueError(f"No active learning cycle for user {user_id}")

        # Get cycle_word with user_word in a single query using JOIN
        cycle_word = (
            self.db.query(CycleWord)
            .join(UserWord, CycleWord.user_word_id == UserWord.id)
            .filter(
                and_(
                    UserWord.user_id == user_id,
                    UserWord.word_id == word_id,
                    CycleWord.cycle_id == learning_cycle.id,
                )
            )
            .first()
        )
        if not cycle_word:
            raise ValueError(f"Word {word_id} not found in cycle {learning_cycle.id}")

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
        user_word.is_learned = True
        user_word.review_stage += 1
        user_word.next_review = self._calculate_next_review(user_word.review_stage)

        self.db.commit()

    def remove_word_from_cycle(self, cycle_id: int, user_word_id: int) -> None:
        """Remove a word from the current cycle."""
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

        self.db.delete(cycle_word)
        self.db.commit()
 
    def _calculate_next_review(self, review_stage: int) -> datetime:
        """Calculate the next review date based on the review stage."""
        x = 1
        if review_stage >= len(settings.learning.repetition_intervals):
            review_stage = len(settings.learning.repetition_intervals) - 1
            x = 10
        days = settings.learning.repetition_intervals[review_stage] * x
        next_review = datetime.now(UTC) + timedelta(days=days)
        return next_review.replace(tzinfo=UTC)  # Ensure timezone awareness

    def get_random_word_texts(self, num_word_texts: int, exclude: Optional[List[str]] = None) -> List[str]:
        """Get random word texts from the database."""
        query = self.db.query(Word.text).distinct()
        if exclude:
            query = query.filter(Word.text.notin_(exclude))
        word_texts = query.all()
        random_word_texts = random.sample(word_texts, min(num_word_texts, len(word_texts)))
        random_word_texts = [word_text[0] for word_text in random_word_texts]
        return random_word_texts

    def get_random_translations(self, num_translations: int, exclude: Optional[List[str]] = None) -> List[str]:
        """Get random translations from the database."""
        query = self.db.query(Word.translation).distinct()
        if exclude:
            query = query.filter(Word.translation.notin_(exclude))
        translations = query.all()
        random_translations = random.sample(translations, min(num_translations, len(translations)))
        random_translations = [translation[0] for translation in random_translations]
        return random_translations

    def get_user_random_translations(self, user_id: int, num_translations: int, exclude: Optional[List[str]] = None) -> List[str]:
        """Get random translations from the user's latest learning cycles."""
        # Get the latest learning cycles for the user
        latest_cycles = (
            self.db.query(LearningCycle)
            .filter(
                and_(
                    LearningCycle.user_id == user_id,
                )
            )
            .order_by(LearningCycle.end_time.desc())
            .limit(3)  # Get translations from last 5 completed cycles
            .all()
        )

        # Get all words from these cycles
        cycle_words = []
        for cycle in latest_cycles:
            words = (
                self.db.query(Word.translation)
                .join(CycleWord, Word.id == CycleWord.user_word_id)
                .join(UserWord, CycleWord.user_word_id == UserWord.id)
                .filter(
                    and_(
                        CycleWord.cycle_id == cycle.id,
                        UserWord.user_id == user_id
                    )
                )
                .distinct()
                .all()
            )
            cycle_words.extend([translation for (translation,) in words])

        # Remove excluded translations if any
        if exclude:
            cycle_words = [word for word in cycle_words if word not in exclude]

        # Return random sample of translations
        return random.sample(cycle_words, min(num_translations, len(cycle_words)))

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

    def mark_cycle_as_completed(self, user_id: int) -> None:
        """Mark the active cycle as completed."""
        cycle = self.get_active_cycle(user_id)
        if not cycle:
            raise ValueError(f"No active learning cycle for user {user_id}")
        cycle.is_completed = True
        cycle.end_time = datetime.now(UTC)
        self.db.commit()

    def get_word(self, word_id: int) -> Optional[Word]:
        """Get a word by its ID."""
        return self.db.query(Word).filter(Word.id == word_id).first()

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

    def get_word_by_id(self, word_id: int) -> Optional[Word]:
        """Get a word by its ID."""
        return self.db.query(Word).filter(Word.id == word_id).first()

    def get_next_word_by_id(self, word_id: int, inverse: bool = False) -> Optional[Word]:
        """Get a word by its ID or the next word if the word is not found."""
        if inverse:
            return self.db.query(Word).filter(Word.id < word_id).order_by(Word.id.desc()).first()
        else:
            return self.db.query(Word).filter(Word.id > word_id).order_by(Word.id).first()

    def get_users_with_active_cycles(self) -> List[int]:
        """Get a list of user IDs that have active learning cycles."""
        # Query users who have active cycles
        user_ids = self.db.query(UserCycle.user_id).distinct().all()
        return [user_id for (user_id,) in user_ids]

    def get_user_cycles(self, user_id: int) -> List[WordProgressData]:
        """Get the active cycles for a user from the database."""
        # Query cycles for this user
        cycles = self.db.query(UserCycle).filter(UserCycle.user_id == user_id).all()
        
        # Convert to WordProgressData objects
        result = []
        for cycle in cycles:
            try:
                # Parse JSON strings
                required_methods = json.loads(cycle.required_methods)
                completed_methods = json.loads(cycle.completed_methods)
                attempts = json.loads(cycle.attempts)
                
                # Create WordProgressData
                data = WordProgressData(
                    word_id=cycle.word_id,
                    required_methods=required_methods,
                    completed_methods=completed_methods,
                    current_method=cycle.current_method,
                    last_attempt=cycle.last_attempt.isoformat() if cycle.last_attempt else None,
                    attempts=attempts
                )
                result.append(data)
                logger.debug(f"Cycle data: {data}")
            except Exception as e:
                logger.error(f"Error parsing cycle data: {e}")
        
        return result

    def save_user_cycles(self, user_id: int, cycles_data: List[WordProgressData]) -> None:
        """Save the active cycles for a user to the database."""
        # Delete existing cycles for this user
        logger.debug(f"Saving cycles for user {user_id}")
        logger.debug(f"Firstly deleting existing cycles for user {user_id}")
        self.db.query(UserCycle).filter(UserCycle.user_id == user_id).delete()
        
        # Add new cycles
        for cycle_data in cycles_data:
            try:
                # if cycle_data.completed:
                #     logger.debug(f"Cycle {cycle_data.word_id} is completed, skipping")
                #     # Mark word as learned
                #     word = self.db.query(UserWord).filter(UserWord.id == cycle_data.word_id).first()
                #     if word:
                #         word.is_learned = True
                #     # Mark cycle as completed
                #     cycle = self.db.query(CycleWord).filter(CycleWord.id == cycle_data.cycle_id).first()
                #     if cycle:
                #         cycle.is_completed = True
                #     continue

                # Convert to JSON strings
                required_methods_json = json.dumps(cycle_data.required_methods)
                completed_methods_json = json.dumps(cycle_data.completed_methods)
                attempts_json = json.dumps(cycle_data.attempts)
                
                # Create UserCycle object
                cycle = UserCycle(
                    user_id=user_id,
                    word_id=cycle_data.word_id,
                    required_methods=required_methods_json,
                    completed_methods=completed_methods_json,
                    current_method=cycle_data.current_method,
                    last_attempt=datetime.fromisoformat(cycle_data.last_attempt) if cycle_data.last_attempt else None,
                    attempts=attempts_json
                )
                
                # Add to session
                self.db.add(cycle)
            except Exception as e:
                logger.error(f"Error saving cycle data: {e}")
        
        # Commit changes
        self.db.commit()

    def delete_user_cycles(self, user_id: int, cycles: Optional[List[WordProgressData]] = None) -> None:
        """Delete cycles for a specific user from the database.
        
        Args:
            user_id: The ID of the user whose cycles should be deleted.
            cycles: Optional list of specific cycles to delete. If None, all cycles for the user will be deleted.
        """
        try:
            query = self.db.query(UserCycle).filter(UserCycle.user_id == user_id)
            if cycles is not None:
                # Delete specific cycles
                word_ids = [cycle.word_id for cycle in cycles]
                query = query.filter(UserCycle.word_id.in_(word_ids))
            
            # Execute deletion
            deleted_count = query.delete()
            self.db.commit()
            logger.debug(f"Deleted {deleted_count} cycles for user {user_id} from database")
        except Exception as e:
            logger.error(f"Error deleting cycles for user {user_id}: {e}")
            self.db.rollback()
            raise

    def delete_user_word(self, user_id: int, word_id: int) -> None:
        """Delete a user word from the database."""
        user_word = self.db.query(UserWord).filter(UserWord.user_id == user_id, UserWord.word_id == word_id).first()
        if not user_word:
            raise ValueError(f"User word {word_id} not found for user {user_id}")
        self.db.query(CycleWord).filter(CycleWord.user_word_id == user_word.id).delete()
        self.db.query(UserCycle).filter(UserCycle.user_id == user_id, UserCycle.word_id == word_id).delete()
        self.db.delete(user_word)
        self.db.commit()

    def delete_word(self, word_id: int) -> None:
        """Delete words from the database."""
        user_words = self.db.query(UserWord).filter(UserWord.word_id == word_id).all()
        for user_word in user_words:
            self.log_user_activity(user_word.user_id, f"Admin deleted word {word_id}", "info", "word")
            self.db.query(CycleWord).filter(CycleWord.user_word_id == user_word.id).delete()
            self.db.query(UserCycle).filter(UserCycle.word_id == user_word.word_id).delete()
            self.db.delete(user_word)
        self.db.query(Word).filter(Word.id == word_id).delete()
        self.db.commit()
