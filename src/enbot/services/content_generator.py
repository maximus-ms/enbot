"""Content generation service using Faker."""
from pathlib import Path
from typing import List, Optional

from faker import Faker

from enbot.config import settings
from enbot.models.models import Example, Word

fake = Faker()


class ContentGenerator:
    """Service for generating word content using Faker."""

    @staticmethod
    def generate_translation(word: str, target_lang: str) -> str:
        """Generate a translation for a word."""
        # In a real implementation, this would use a translation API
        # For now, we'll just return a fake translation
        return fake.word()

    @staticmethod
    def generate_transcription(word: str) -> str:
        """Generate a transcription for a word."""
        # In a real implementation, this would use a transcription API
        # For now, we'll just return a fake transcription
        return fake.word()

    @staticmethod
    def generate_pronunciation(word: str) -> str:
        """Generate a pronunciation file path for a word."""
        # In a real implementation, this would generate an audio file
        # For now, we'll just return a fake file path
        filename = f"{word.lower().replace(' ', '_')}.mp3"
        return str(Path(settings.PRONUNCIATIONS_DIR) / filename)

    @staticmethod
    def generate_image(word: str) -> str:
        """Generate an image file path for a word."""
        # In a real implementation, this would generate an image file
        # For now, we'll just return a fake file path
        filename = f"{word.lower().replace(' ', '_')}.jpg"
        return str(Path(settings.IMAGES_DIR) / filename)

    @staticmethod
    def generate_examples(word: str, translation: str, count: int = 3) -> List[Example]:
        """Generate example sentences for a word."""
        examples = []
        for _ in range(count):
            example = Example(
                sentence=fake.sentence(),
                translation=fake.sentence(),
                is_good=True,
            )
            examples.append(example)
        return examples

    @classmethod
    def generate_word_content(
        cls,
        word: str,
        target_lang: str,
        native_lang: str,
    ) -> tuple[Word, List[Example]]:
        """Generate all content for a word."""
        translation = cls.generate_translation(word, target_lang)
        transcription = cls.generate_transcription(word)
        pronunciation_file = cls.generate_pronunciation(word)
        image_file = cls.generate_image(word)
        examples = cls.generate_examples(word, translation)

        word_obj = Word(
            text=word,
            translation=translation,
            transcription=transcription,
            pronunciation_file=pronunciation_file,
            image_file=image_file,
            language_pair=f"{target_lang}-{native_lang}",
        )

        return word_obj, examples 