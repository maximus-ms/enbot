"""Models for training-related data structures."""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import logging
from enbot.models.models import Word


logger = logging.getLogger(__name__)


class UserAction(Enum):
    """Possible user actions during training."""
    ANSWER = "answer"  # User provided an answer
    SKIP = "skip"  # User skipped the word
    MARK_LEARNED = "mark_learned"  # User marked word as learned
    MORE_INFO = "more_info"  # User requested more information
    DELETE = "delete"  # User wants to delete the word
    PREVIOUS = "previous"  # User wants to go to the previous word

@dataclass
class TrainingRequest:
    """Represents a request for training a word."""
    method: Any #TrainingMethod
    word: Word
    message: str
    buttons: List[Dict[str, str]]
    expects_text: bool = False
    additional_data: Dict[str, Any] = None


@dataclass
class RawResponse:
    """Represents user's raw response to a training request."""
    request: TrainingRequest
    text: str = None


@dataclass
class UserResponse:
    """Represents user's response to a training request."""
    action: UserAction
    word_id: int
    answer: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
