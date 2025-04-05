"""Models for cycle-related data."""
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class WordProgressData:
    """Serializable version of WordProgress for database storage."""
    word_id: int
    required_methods: List[str]  # List of TrainingMethod values as strings
    completed_methods: List[str]
    current_method: Optional[str]
    last_attempt: Optional[str]  # ISO format datetime string
    attempts: Dict[str, int]  # Method name -> attempt count
