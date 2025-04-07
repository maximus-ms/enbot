"""Service for managing word learning cycles."""
import logging
import random
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any, Set, Type, ClassVar, final
import threading
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from enbot.models.models import UserWord, Word, User
from enbot.models.cycle_models import WordProgressData
from enbot.models.training_models import TrainingRequest, RawResponse, UserResponse, UserAction
from enbot.services.learning_service import LearningService
from enbot.services.training_methods import TrainingMethod, get_all_subclasses, BaseTrainingMethod


logger = logging.getLogger(__name__)


class WordProgress:
    """Tracks progress of a word through different training methods."""
    method_priority_map = {}

    def __init__(self, word: Word, required_methods: Set[TrainingMethod]):
        self.word = word
        self.required_methods = required_methods
        self.completed_methods: Set[TrainingMethod] = set()
        self.current_method: Optional[TrainingMethod] = None
        self.last_attempt: Optional[datetime] = None
        self.attempts: Dict[TrainingMethod, int] = {method: 0 for method in required_methods}
        self.is_completed = False
        if not len(WordProgress.method_priority_map):
            try:
                all_subclasses = get_all_subclasses(BaseTrainingMethod)
                logger.debug(f"All subclasses: {all_subclasses}")
                for method_class in all_subclasses:
                    logger.debug(f"Method class: {method_class.__name__}")
                    logger.debug(f"Method type: {method_class.type}")
                    logger.debug(f"Method priority: {method_class.priority}")
                    WordProgress.method_priority_map[method_class.type] = method_class.priority
            except Exception as e:
                logger.error(f"Error getting method priority map: {e}")

    def is_complete(self) -> bool:
        """Check if all required methods are completed."""
        return self.completed_methods == self.required_methods

    def get_next_method(self, last_word_in_cycle: bool, previous_method: Optional[TrainingMethod] = None) -> Optional[TrainingMethod]:
        """Get the next method to try, prioritizing incomplete methods."""
        logger.debug(f"Getting next method for word {self.word.id}, last_word_in_cycle: {last_word_in_cycle}, previous_method: {previous_method}")
        self.current_method = None
        if last_word_in_cycle and len(self.required_methods) == 1:
            logger.error("Last word in cycle and only one method required")
            return None

        incomplete = self.required_methods - self.completed_methods
        if not incomplete:
            return None

        logger.debug(f"Incomplete methods0: {incomplete}")
        if last_word_in_cycle and previous_method:
            incomplete -= set([previous_method])
        logger.debug(f"Incomplete methods1: {incomplete}")
        
        if not incomplete:
            incomplete = self.completed_methods
        logger.debug(f"Incomplete methods3: {incomplete}")

        # Sort methods by attempts and priority
        new_methods = sorted(incomplete, key=lambda m: (self.attempts[m], WordProgress.method_priority_map[m]))[:2]
        logger.debug(f"New methods: {new_methods}")
        new_method = random.choice(new_methods)
        logger.debug(f"New method:  {new_method}")
        self.current_method = new_method
        return new_method

    def mark_completed(self, method: TrainingMethod = None) -> None:
        """Mark a method as completed."""
        if method:
            self.completed_methods.add(method)
        else:
            self.completed_methods = self.required_methods
        # self.current_method = None

    def record_attempt(self, method: TrainingMethod, success: bool) -> None:
        """Record an attempt at a method."""
        self.attempts[method] += 1
        if success:
            self.mark_completed(method)
        self.last_attempt = datetime.now()

    def to_data(self) -> WordProgressData:
        """Convert to serializable data for storage."""
        return WordProgressData(
            word_id=self.word.id,
            required_methods=[m.value for m in self.required_methods],
            completed_methods=[m.value for m in self.completed_methods],
            current_method=self.current_method.value if self.current_method else None,
            last_attempt=self.last_attempt.isoformat() if self.last_attempt else None,
            attempts={m.value: count for m, count in self.attempts.items()},
        )

    @classmethod
    def from_data(cls, data: WordProgressData, word: Word) -> 'WordProgress':
        """Create a WordProgress instance from stored data."""
        progress = cls(
            word=word,
            required_methods={TrainingMethod(m) for m in data.required_methods}
        )
        progress.completed_methods = {TrainingMethod(m) for m in data.completed_methods}
        progress.current_method = TrainingMethod(data.current_method) if data.current_method else None
        progress.last_attempt = datetime.fromisoformat(data.last_attempt) if data.last_attempt else None
        progress.attempts = {TrainingMethod(m): count for m, count in data.attempts.items()}
        return progress


class CycleService:
    """Service for managing word learning cycles."""
    _instance: ClassVar[Optional['CycleService']] = None
    _lock = threading.Lock()
    
    # Class-level fields (shared across all instances)
    methods: Dict[TrainingMethod, BaseTrainingMethod] = {}
    methods_whitelist: Set[TrainingMethod] = set([
        TrainingMethod.REMEMBER,
        TrainingMethod.REMEMBER2,
    ])
    active_cycles: Dict[int, List[WordProgress]] = {}
    _last_cleanup: float = 0
    _cycle_timeout: int = 3600  # 1 hour
    CALLBACK_PREFIX: str = BaseTrainingMethod.CALLBACK_PREFIX
    
    def __init__(self, learning_service: LearningService):
        """Initialize the cycle service."""

        # Instance field (unique per instance)
        self.learning_service = learning_service
        
        if not len(self.methods):
            try:
                all_subclasses = get_all_subclasses(BaseTrainingMethod)
                for method_class in all_subclasses:
                    if not method_class.type in self.methods_whitelist: continue
                    self.methods[method_class.type] = method_class
            except Exception as e:
                logger.error(f"Error getting method classes: {e}")

        # # Initialize all training methods
        # self.training_methods: List[BaseTrainingMethod] = [
        #     RememberMethod(learning_service),
        #     Remember2Method(learning_service),
        #     # TODO: enable other methods
        #     # MultipleChoiceMethod(learning_service),
        #     # SpellingMethod(learning_service),
        #     # TranslationMethod(learning_service),
        # ]

        # Load active cycles from database
        self._load_active_cycles()

        # Run cleanup if needed
        self._run_cleanup_if_needed()

    @classmethod
    def get_instance(cls, learning_service: LearningService) -> 'CycleService':
        """Get the singleton instance of the cycle service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(learning_service)
            else:
                logger.debug(f"Returning existing instance of {cls.__name__}, learning_service will be ignored")
            return cls._instance
    
    def _run_cleanup_if_needed(self) -> None:
        """Run cleanup of old cycles if enough time has passed."""
        current_time = time.time()
        logger.debug(f"Running cleanup (if needed) of old cycles, last cleanup: {CycleService._last_cleanup}, current time: {current_time}, cleanup interval: {CycleService._cycle_timeout}")
        if current_time - CycleService._last_cleanup > CycleService._cycle_timeout:
            logger.debug("Running cleanup of old cycles")
            self._cleanup_old_cycles()
            CycleService._last_cleanup = current_time
    
    def _delete_user_cycles(self, user_id: int, cycles: Optional[List[WordProgress]] = None) -> None:
        """Delete cycles for a specific user from the database."""
        try:
            # Convert cycles to serializable data
            cycles_data = [cycle.to_data() for cycle in cycles]
            
            # Save to database
            self.learning_service.delete_user_cycles(user_id, cycles_data)
            logger.info(f"Deleted {len(cycles)} cycles for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting cycles for user {user_id}: {e}")

    def _cleanup_old_cycles(self) -> None:
        """Remove cycles that haven't been accessed in a while."""
        current_time = time.time()
        for user_id, cycles in list(self.active_cycles.items()):
            # Check if any cycle has been accessed recently
            has_recent_activity = any(
                cycle.last_attempt and 
                (current_time - cycle.last_attempt.timestamp()) < self._cycle_timeout
                for cycle in cycles
            )
            
            if not has_recent_activity:
                # Delete from database before removing from memory
                self._delete_user_cycles(user_id, cycles)
                del self.active_cycles[user_id]
                logger.info(f"Cleaned up inactive cycles for user {user_id}")
    
    def _load_active_cycles(self) -> None:
        """Load active cycles from the database."""
        logger.debug("Loading active cycles")
        try:
            # Get all user IDs with active cycles
            user_ids = self.learning_service.get_users_with_active_cycles()
            logger.debug(f"Found {len(user_ids)} users with active cycles")
            for user_id in user_ids:
                # Load cycles for this user
                cycles_data = self.learning_service.get_user_cycles(user_id)
                if not cycles_data:
                    continue
                
                # Convert data to WordProgress objects
                cycles = []
                for cycle_data in cycles_data:
                    try:
                        # Get the word
                        word = self.learning_service.get_word_by_id(cycle_data.word_id)
                        if not word:
                            continue
                            
                        # Create WordProgress from data
                        progress = WordProgress.from_data(cycle_data, word)
                        cycles.append(progress)
                        logger.debug(f"Cycle data: {progress}")
                    except Exception as e:
                        logger.error(f"Error loading cycle data: {e}")
                
                if cycles:
                    self.active_cycles[user_id] = cycles
                    logger.info(f"Loaded {len(cycles)} active cycles for user {user_id}")
                else:
                    logger.debug(f"No active cycles found for user {user_id}")
        except Exception as e:
            logger.error(f"Error loading active cycles: {e}")
    
    def _save_user_cycles(self, user_id: int, cycles: List[WordProgress]) -> None:
        """Save cycles for a specific user to the database."""
        try:
            # Convert cycles to serializable data
            cycles_data = [cycle.to_data() for cycle in cycles]
            
            # Save to database
            self.learning_service.save_user_cycles(user_id, cycles_data)
            logger.info(f"Saved {len(cycles)} cycles for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving cycles for user {user_id}: {e}")
    
    def _save_all_cycles(self) -> None:
        """Save all active cycles to the database."""
        for user_id, cycles in self.active_cycles.items():
            self._save_user_cycles(user_id, cycles)
    
    def save_state(self) -> None:
        """Save the current state to the database."""
        self._save_all_cycles()
    
    def _get_required_methods(self, word: Word) -> Set[TrainingMethod]:
        """Determine which methods are required for a word."""
        required_methods = set()
        
        # Check each method to see if it should be used for this word
        for method_class in self.methods.values():
            if method_class.should_be_used_for_word(word):
                required_methods.add(method_class.type)
                
        return required_methods

    def _create_word_progress(self, word: Word) -> WordProgress:
        """Create a new WordProgress object for a word."""
        required_methods = self._get_required_methods(word)
        return WordProgress(word, required_methods)

    def get_next_word(self, user_id: int, previous_progress: WordProgress = None) -> Optional[TrainingRequest]:
        """Get the next word to train for a user."""
        logger.debug(f"Getting next word for user {user_id}, previous_progress: {previous_progress}")
        # Get active cycle
        cycle = self.active_cycles.get(user_id)
        if not cycle:
            logger.debug(f"No active cycles for user {user_id}, creating new cycle")
            words, _ = self.learning_service.get_words_for_cycle_or_create(user_id)
            cycle = [
                self._create_word_progress(word.word) for word in words
            ]
            self.active_cycles[user_id] = cycle
            if not cycle:
                logger.debug(f"No active cycles for user {user_id}")
                return None
            else:
                logger.debug(f"Cycle created for user {user_id}: {cycle}")
            # Save the new cycles
            self._save_user_cycles(user_id, cycle)
        else:
            logger.debug(f"Active cycles for user {user_id} restored from active_cycles cache")

        logger.debug(f"Getting next word for user {user_id}")
        # Find word with incomplete methods

        progress = random.choice(cycle)
        last_word_in_cycle = len(cycle) == 1
        if previous_progress:
            previous_word_id = previous_progress.word.id
            previous_method = previous_progress.current_method
            while not last_word_in_cycle and progress.word.id == previous_word_id:
                progress = random.choice(cycle)
        else:
            previous_word_id = None
            previous_method = None

        logger.debug(f"Previous progress: word {previous_word_id}, method {previous_method}")
        next_method = progress.get_next_method(last_word_in_cycle, previous_method)
        if next_method:
            logger.debug(f"Next method for user {user_id}: {next_method}")
            return self._create_training_request(progress)

        logger.debug(f"No incomplete methods for user {user_id}")
        return None

    def _create_training_request(self, progress: WordProgress, extra_actions: List[UserAction] = []) -> TrainingRequest:
        """Create a training request for a specific method."""
        logger.debug(f"Creating training request for method: {progress.current_method}, progress: {progress}")
        # Find the appropriate method class
        method_class = self.methods.get(progress.current_method)
        if not method_class:
            logger.error(f"Unknown training method: {progress.current_method}")
            raise ValueError(f"Unknown training method: {progress.current_method}")
            
        return method_class(self.learning_service).create_request(progress.word, extra_actions)

    def process_response_and_get_next_request(self, user_id: int, raw_response: RawResponse) -> Optional[TrainingRequest]:
        """Process user's response and return next training request if any."""
        cycle = self.active_cycles.get(user_id)
        if not cycle:
            return None

        # Find the word progress
        word_progress = next((wp for wp in cycle if wp.word.id == raw_response.request.word.id), None)
        if not word_progress:
            return None

        # find the method class
        method_class = self.methods.get(raw_response.request.method)
        method_entity = method_class(self.learning_service)
        if not method_entity:
            return None

        response = method_entity.parse_response(raw_response)
        if not response:
            return None
        
        word_progress.current_method = method_entity.type
        use_the_same_word_and_method = False
        extra_actions = []
        # Process the response based on action
        if response.action == UserAction.MARK_LEARNED:
            logger.debug(f"Marking word {word_progress.word.id} as learned in total")
            word_progress.mark_completed()
        elif response.action == UserAction.SKIP:
            logger.debug(f"Skipping word {word_progress.word.id} for now")
        elif response.action == UserAction.ANSWER_YES:
            logger.debug(f"Marking word {word_progress.word.id} as learned by method {word_progress.current_method}")
            word_progress.record_attempt(word_progress.current_method, True)
        elif response.action == UserAction.ANSWER_NO:
            logger.debug(f"Skipping word {word_progress.word.id} for now, method {word_progress.current_method}")
            word_progress.record_attempt(word_progress.current_method, False)
        elif response.action == UserAction.PRONOUNCE:
            logger.debug(f"Pronouncing word {word_progress.word.id}")
            word_progress.record_attempt(word_progress.current_method, False)
            use_the_same_word_and_method = True
            extra_actions.append(UserAction.PRONOUNCE)
        elif response.action == UserAction.SHOW_EXAMPLES:
            logger.debug(f"Showing examples for word {word_progress.word.id}")
            word_progress.record_attempt(word_progress.current_method, False)
            use_the_same_word_and_method = True
            extra_actions.append(UserAction.SHOW_EXAMPLES)
        else:
            logger.debug(f"Unknown action: {response.action}")

        # elif response.action == UserAction.ANSWER:
        #     # Find the appropriate method class
        #     method_entity = next((m for m in self.training_methods if m.type == word_progress.current_method), None)
        #     if method_entity:
        #         # Check if answer is correct
        #         is_correct = method_entity.parse_response(response, self._create_training_request(word_progress, word_progress.current_method))
        #         word_progress.record_attempt(word_progress.current_method, is_correct)

        # Check if word is complete
        if word_progress.is_complete():
            logger.debug(f"Word {word_progress.word.id} is complete, marking as learned")
            # Mark word as learned in database
            self.learning_service.mark_word_as_learned(user_id, word_progress.word.id, time_spent=0) # TODO: add time spent
            # Save the updated cycles
            # self._save_user_cycles(user_id, cycle)
            # Remove from active cycle
            cycle.remove(word_progress)
            # Save the updated cycles
            self._save_user_cycles(user_id, cycle)
        else:
            logger.debug(f"Word {word_progress.word.id} is not complete, noncomplete methods: {word_progress.required_methods - word_progress.completed_methods}")
            self._save_user_cycles(user_id, cycle)

        # Get next word to train
        if not cycle:
            self.learning_service.mark_cycle_as_completed(user_id)
            return None
        
        if use_the_same_word_and_method:
            return self._create_training_request(word_progress, extra_actions)
        else:
            return self.get_next_word(user_id, word_progress)
