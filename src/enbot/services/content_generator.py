"""Content generation service using Faker."""
from pathlib import Path
from typing import List, Optional
import os
import re
import random
from faker import Faker

from enbot.config import settings
from enbot.models.models import Example, Word

fake = Faker()


class ContentGenerator:
    """Service for generating word content using Faker."""

    @staticmethod
    def generate_translation(word: str, target_lang: str, native_lang: str) -> str:
        """Generate a translation for a word."""
        # In a real implementation, this would use a translation API
        # For now, we'll just return a fake translation
        # return fake.word() if len(word.split()) == 1 else fake.sentence()
        return word

    @staticmethod
    def generate_transcription(word: str, target_lang: str) -> str:
        """Generate a transcription for a word."""
        # In a real implementation, this would use a transcription API
        # For now, we'll just return a fake transcription
        # return fake.word()
        return word

    @staticmethod
    def generate_pronunciation(word: str, target_lang: str) -> str:
        """Generate a pronunciation file path for a word."""
        # In a real implementation, this would generate an audio file
        # For now, we'll just return a fake file path
        filename = f"{ContentGenerator._sanitize_filename(word)}.mp3"
        return str(settings.paths.pronunciations_dir / filename)

    @staticmethod
    def generate_image(word: str) -> str:
        """Generate an image file path for a word."""
        # In a real implementation, this would generate an image file
        # For now, we'll just return a fake file path
        filename = f"{ContentGenerator._sanitize_filename(word)}.jpg"
        return str(settings.paths.images_dir / filename)

    @staticmethod
    def generate_example(word: str, target_lang: str, native_lang: str) -> str:
        """Generate example sentence for a word."""
        sentence = fake.sentence()
        translation = ContentGenerator.generate_translation(sentence, target_lang, native_lang)
        return Example(
            sentence=sentence,
            translation=translation,
            is_good=True,
        )

    @staticmethod
    def generate_examples(word: str, target_lang: str, native_lang: str, count: int = 3) -> List[Example]:
        """Generate example sentences for a word."""
        examples = []
        for _ in range(count):
            example = ContentGenerator.generate_example(word, target_lang, native_lang)
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
        translation = cls.generate_translation(word, target_lang, native_lang)
        transcription = cls.generate_transcription(word, target_lang)
        pronunciation_file = cls.generate_pronunciation(word, target_lang)
        image_file = cls.generate_image(word)
        examples_count = random.randint(settings.content.min_examples, settings.content.max_examples)
        examples = cls.generate_examples(word, target_lang, native_lang, examples_count)

        word_obj = Word(
            text=word,
            translation=translation,
            transcription=transcription,
            pronunciation_file=pronunciation_file,
            image_file=image_file,
            language_pair=f"{target_lang}-{native_lang}",
        )

        return word_obj, examples

    @staticmethod
    def delete_file(file_path: str) -> None:
        """Delete a file from storage."""
        if os.path.exists(file_path):
            os.remove(file_path)

    @staticmethod
    def _sanitize_filename(word: str) -> str:
        """Sanitize word for use in filename."""
        # Replace any non-alphanumeric characters with underscore
        return re.sub(r'[^a-zA-Z0-9]', '_', word.lower())
