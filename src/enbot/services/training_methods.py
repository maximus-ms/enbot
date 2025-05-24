"""Training methods for word learning."""
import logging
from abc import ABC, abstractmethod
from typing import final, List, Dict
from enum import Enum
from enbot.models.training_models import TrainingRequest, RawResponse, UserResponse, UserAction
from enbot.models.models import Word
from enbot.services.learning_service import LearningService
import random


logger = logging.getLogger(__name__)


class TrainingMethod(Enum):
    """Available training methods."""
    BASE = "base"  # Base method
    REMEMBER = "remember"  # Simple remember/don't remember
    MULTIPLE_CHOICE_NATIVE = "multiple_choice_native"  # Choose from options
    MULTIPLE_CHOICE_TARGET = "multiple_choice_target"  # Choose from options
    SPELLING = "spelling"  # Spell the word
    TRANSLATION = "translation"  # Translate to/from English
    # TYPE_WORD = "type_word"  # Type the word


def get_all_subclasses(cls):
    """Get all subclasses of a class."""
    all_subclasses = []
    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))
    return all_subclasses


class BaseTrainingMethod(ABC):
    """Base class for all training methods."""

    """Fields and methods that must be implemented by subclasses."""
    type: TrainingMethod = TrainingMethod.BASE
    priority: int = 0

    @abstractmethod
    def _create_request(self, word: Word) -> TrainingRequest:
        """Internal method to create a training request. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _parse_response(self, callback_data: str, raw_response: RawResponse) -> UserResponse:
        """Parse user's response and determine if it's correct."""
        logger.debug(f"Default method: Parsing response for callback_data: {callback_data}")
        if not callback_data.startswith("answer"): return None
        return UserResponse(raw_response.request.word.id, UserAction(callback_data))
    
    @classmethod
    def should_be_used_for_word(cls, word: Word) -> bool:
        """Determine if this method should be used for the given word."""
        return False

    """Fields and methods that must not be overridden by subclasses."""
    CALLBACK_PREFIX: str = "cycle_"

    @final
    def __init__(self, learning_service: LearningService):
        self.learning_service = learning_service
        self.callback_prefix = BaseTrainingMethod.CALLBACK_PREFIX
    
    @final
    def _add_callback_prefix_to_list_of_buttons(self, buttons: List[Dict[str, str]]) -> List[Dict[str, str]]:
        for button in buttons:
            if isinstance(button, list):
                self._add_callback_prefix_to_list_of_buttons(button)
            else:
                button["callback_data"] = f"{self.callback_prefix}{button['callback_data']}"
        return buttons
    
    @final
    def create_request(self, word: Word, extra_actions: List[UserAction] = []) -> TrainingRequest:
        """Create a training request for this method."""
        if UserAction.SHOW_CORRECT_ANSWER in extra_actions:
            request = TrainingRequest(
                method=self.type,
                word=word,
                message="Correct answer:\n\n",
                buttons=[
                    [{"text": "🔊 Pronounce", "callback_data": f"basepronounce"},
                     {"text": "➡️ Next word", "callback_data": UserAction.ANSWER_NO.value}],
                ]
            )
            request.message += f"<b>{word.text}</b> - <i>{word.translation}</i>"
            extra_actions.remove(UserAction.SHOW_CORRECT_ANSWER)
            extra_actions.append(UserAction.SHOW_EXAMPLES)
        else:
            request = self._create_request(word)
            
            request.buttons.extend([
                # {"text": "🔙 Back", "callback_data": f"{self.callback_prefix}back"},
                [{"text": "🔊 Pronounce", "callback_data": f"basepronounce"},
                 {"text": "📝 Examples",  "callback_data": f"baseexamples"}],
            ])
        request.buttons.extend([
            [{"text": "🗑️ Delete",    "callback_data": f"basedelete"},
             {"text": "✔️ I know it", "callback_data": f"baseknown"}]
        ])
        
        for action in extra_actions:
            if action == UserAction.SHOW_EXAMPLES:
                request.message += "\n\n📝 Examples:"
                for example in word.examples:
                    request.message += f"\n<b>{example.sentence}</b> - <i>{example.translation}</i>"
        request.buttons = self._add_callback_prefix_to_list_of_buttons(request.buttons)
        return request
    
    @final
    def parse_response(self, raw_response: RawResponse) -> UserResponse:
        """Parse user's response and determine if it's correct."""
        callback_data = raw_response.text[len(self.callback_prefix):]
        action = callback_data.split("_", 1)[0]
        
        if action == "baseknown":
            return UserResponse(raw_response.request.word.id, UserAction.MARK_LEARNED)
        elif action == "basedelete":
            return UserResponse(raw_response.request.word.id, UserAction.DELETE)
        elif action == "basepronounce":
            return UserResponse(raw_response.request.word.id, UserAction.PRONOUNCE)
        elif action == "baseexamples":
            return UserResponse(raw_response.request.word.id, UserAction.SHOW_EXAMPLES)
        elif action == UserAction.SHOW_CORRECT_ANSWER.value:
            return UserResponse(raw_response.request.word.id, UserAction.SHOW_CORRECT_ANSWER)
        else:
            return self._parse_response(callback_data, raw_response)

    @final  
    def get_method_name(self) -> str:
        """Get the TrainingMethod enum value for this method."""
        return self.type.value
    

class RememberMethod(BaseTrainingMethod):
    """Simple method to remember the word."""
    type: TrainingMethod = TrainingMethod.REMEMBER
    priority: int = 1

    @classmethod
    def should_be_used_for_word(cls, word: Word) -> bool:
        """This method can be used for any word."""
        return True

    def _create_request(self, word: Word) -> TrainingRequest:
        logger.debug(f"RememberMethod: Creating training request for word: {word}")
        return TrainingRequest(
            method=self.type,
            word=word,
            message=f"Do you know this word?\n\n<b>{word.text}</b> - <i>{word.translation}</i>",
            buttons=[
                [{"text": "📝 Study more", "callback_data": UserAction.ANSWER_NO.value},
                 {"text": "⭐ Remember",   "callback_data": UserAction.ANSWER_YES.value}],
            ]
        )


class MultipleChoiceNativeMethod(BaseTrainingMethod):
    """Method with multiple choice options."""
    priority: int = 2
    type: TrainingMethod = TrainingMethod.MULTIPLE_CHOICE_NATIVE

    @classmethod
    def should_be_used_for_word(cls, word: Word) -> bool:
        """This method can be used for any word."""
        return True
    
    def _create_request(self, word: Word) -> TrainingRequest:
        # Create multiple choice options
        options = [word.translation]  # Correct answer
        # Add 3 random wrong options
        wrong_options = self.learning_service.get_random_translations(3, exclude=[word.translation])
        options.extend(wrong_options)
        # Create a list of indexes and shuffle it
        option_indexes = list(range(len(options)))
        random.shuffle(option_indexes)

        buttons = [
            [{"text": options[i], "callback_data": UserAction.ANSWER_YES.value if 0 == i else UserAction.SHOW_CORRECT_ANSWER.value}]
            for i in option_indexes
        ]
        buttons.append([{"text": "❓ I don't know", "callback_data": UserAction.SHOW_CORRECT_ANSWER.value}])
        
        return TrainingRequest(
            method=self.type,
            word=word,
            message=f"Choose the correct translation for:\n\n<b>{word.text}</b>",
            buttons=buttons,
        )


class MultipleChoiceTargetMethod(BaseTrainingMethod):
    """Method with multiple choice options."""
    priority: int = 3
    type: TrainingMethod = TrainingMethod.MULTIPLE_CHOICE_TARGET

    @classmethod
    def should_be_used_for_word(cls, word: Word) -> bool:
        """This method can be used for any word."""
        return True
    
    def _create_request(self, word: Word) -> TrainingRequest:
        # Create multiple choice options
        options = [word.text]  # Correct answer
        # Add 3 random wrong options
        wrong_options = self.learning_service.get_random_word_texts(3, exclude=[word.text])
        options.extend(wrong_options)
        # Create a list of indexes and shuffle it
        option_indexes = list(range(len(options)))
        random.shuffle(option_indexes)

        buttons = [
            [{"text": options[i], "callback_data": UserAction.ANSWER_YES.value if 0 == i else UserAction.SHOW_CORRECT_ANSWER.value}]
            for i in option_indexes
        ]
        buttons.append([{"text": "❓ I don't know", "callback_data": UserAction.SHOW_CORRECT_ANSWER.value}])
        
        return TrainingRequest(
            method=self.type,
            word=word,
            message=f"Choose the correct variant for:\n\n<b>{word.translation}</b>",
            buttons=buttons,
        )


class SpellingMethod(BaseTrainingMethod):
    """Method where user needs to spell the word."""
    priority: int = 4
    type: TrainingMethod = TrainingMethod.SPELLING

    @classmethod
    def should_be_used_for_word(cls, word: Word) -> bool:
        """Use for longer words."""
        return len(word.text) > 6
    
    def _create_request(self, word: Word) -> TrainingRequest:
        return TrainingRequest(
            method=self.type,
            word=word,
            message=f"Type the word for this translation:\n\n<b>{word.translation}</b>",
            buttons=[{"text": "🔙 Back", "callback_data": f"{self.callback_prefix}back"}],
            expects_text=True
        )
    
    def _parse_response(self, raw_response: RawResponse) -> UserResponse:
        if not raw_response.text:
            return False
        return UserResponse(UserAction.ANSWER, raw_response.request.word.id, raw_response.text.lower() == raw_response.request.word.text.lower())


class TranslationMethod(BaseTrainingMethod):
    """Method where user needs to translate a sentence."""
    priority: int = 5
    type: TrainingMethod = TrainingMethod.TRANSLATION

    @classmethod
    def should_be_used_for_word(cls, word: Word) -> bool:
        """Use for words with examples."""
        return bool(word.examples)
    
    def _create_request(self, word: Word) -> TrainingRequest:
        example = random.choice(word.examples)
        return TrainingRequest(
            method=self.type,
            word=word,
            message=f"Translate this sentence:\n\n<b>{example.sentence}</b>\n\nTranslation: <i>{example.translation}</i>",
            buttons=[{"text": "🔙 Back", "callback_data": f"{self.callback_prefix}back"}],
            expects_text=True,
            additional_data={"example": example}
        )
    
    def _parse_response(self, raw_response: RawResponse) -> UserResponse:
        if not raw_response.text:
            return False
        # Simple check for now - could be more sophisticated
        return UserResponse(UserAction.ANSWER, raw_response.request.word.id, raw_response.text.lower() in raw_response.request.word.translation.lower())
