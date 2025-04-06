"""Content generation service using Faker."""
from pathlib import Path
from typing import List, Optional
import os
import re
import random
import logging
from datetime import datetime, timedelta
from faker import Faker
from deep_translator import GoogleTranslator
from gtts import gTTS
import eng_to_ipa as ipa
import nltk
from nltk.corpus import wordnet

from enbot.config import settings
from enbot.models.models import Example, Word

logger = logging.getLogger(__name__)

class ContentGenerator:
    """Service for generating word content using Faker."""
    _instance = None
    _initialized = False
    _last_check = None
    _check_interval = timedelta(days=7)  # Check for updates every 7 days

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ContentGenerator, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not ContentGenerator._initialized:
            self._check_and_update_nltk()
            self.faker = Faker()
            ContentGenerator._initialized = True
            logger.info("ContentGenerator initialized")

    def _check_and_update_nltk(self):
        """Check and update NLTK data if needed."""
        current_time = datetime.now()
        
        # Check if we need to verify updates
        if (ContentGenerator._last_check is None or 
            current_time - ContentGenerator._last_check > ContentGenerator._check_interval):
            
            try:
                # Check if wordnet is installed
                nltk.data.find('corpora/wordnet')
                
                # Try to update NLTK data
                try:
                    nltk.download('wordnet', quiet=True)
                    logger.info("Checked for NLTK wordnet updates")
                except Exception as e:
                    logger.warning(f"Could not update NLTK data: {e}")
                
            except LookupError:
                # Wordnet is not installed, download it
                nltk.download('wordnet', quiet=True)
                logger.info("Downloaded NLTK wordnet data")
            
            ContentGenerator._last_check = current_time

    @staticmethod
    def generate_translation(word: str, target_lang: str, native_lang: str) -> str:
        """Generate a translation for a word."""
        try:
            translator = GoogleTranslator(source=target_lang, target=native_lang)
            translation = translator.translate(word)
            logger.info(f"Translation generated for word: {word}, translation: {translation}")
            return translation
        except Exception as e:
            logger.error(f"Error generating translation for word: {word}, error: {e}")
            return ""

    @staticmethod
    def generate_transcription(word: str, target_lang: str) -> str:
        """Generate a transcription for a word."""
        # In a real implementation, this would use a transcription API
        # For now, we'll just return a fake transcription
        # return fake.word()
        if target_lang == "en" and len(word.split()) == 1:
            try:
                transcription = ipa.convert(word)
                logger.info(f"Transcription generated for word: {word}, transcription: {transcription}")
                return transcription
            except Exception as e:
                logger.error(f"Error generating transcription for word: {word}, error: {e}")
                return ""
        return ""

    @staticmethod
    def generate_pronunciation(word: str, target_lang: str) -> str:
        """Generate a pronunciation file path for a word."""
        # In a real implementation, this would generate an audio file
        # For now, we'll just return a fake file path
        filename = f"{ContentGenerator._sanitize_filename(word)}.mp3"
        try:
            tts = gTTS(text=word, lang=target_lang)
            tts.save(str(settings.paths.pronunciations_dir / filename))
            logger.info(f"Pronunciation generated for word: {word}, file: {filename}")
            return str(settings.paths.pronunciations_dir / filename)
        except Exception as e:
            logger.error(f"Error generating pronunciation for word: {word}, error: {e}")
            return ""

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
        synsets = wordnet.synsets(word)
        if synsets:
            syn = synsets[0]
            examples = syn.examples()
            if examples:
                sentence = random.choice(examples)
        else:
            sentence = ""
        translation = ContentGenerator.generate_translation(sentence, target_lang, native_lang)
        return Example(
            sentence=sentence,
            translation=translation,
            is_good=True,
        )

    @staticmethod
    def generate_examples(word: str, target_lang: str, native_lang: str, count: int = 3, sentences: Optional[List[str]] = None) -> List[Example]:
        """Generate example sentences for a word."""
        sentences_examples = []
        if not sentences:
            synsets = wordnet.synsets(word)
            try:
                if synsets:
                    syn = synsets[0]
                    sentences_examples = syn.examples()
                if sentences_examples:
                    sentences = random.sample(sentences_examples, min(count, len(sentences_examples)))
                    for i in range(len(sentences)):
                        translation=ContentGenerator.generate_translation(sentences[i], target_lang, native_lang)
                        sentences[i] = f"{sentences[i]} ; {translation}"
            except Exception as e:
                logger.error(f"Error generating examples for word: {word}, error: {e}")

        if not sentences: return []

        examples = []
        for sentence in sentences:
            try:
                sentence, translation = sentence.split(" ; ")
                example = Example(
                    sentence=sentence,
                    translation=translation,
                    is_good=True,
                )
                examples.append(example)
                logger.info(f"Example generated for word: {word}, example: {examples}")
            except Exception as e:
                logger.error(f"Error generating example for word: {word}, error: {e}")
                continue
        logger.debug(f"Examples generated for word: {word}, examples: {examples}")
        return examples

    @classmethod
    def generate_word_content(
        cls,
        word: str,
        target_lang: str,
        native_lang: str,
        translation: Optional[str] = None,
        user_examples: Optional[List[Example]] = None,
    ) -> tuple[Word, List[Example]]:
        """Generate all content for a word."""
        if translation is None:
            translation = cls.generate_translation(word, target_lang, native_lang)
        transcription = cls.generate_transcription(word, target_lang)
        pronunciation_file = cls.generate_pronunciation(word, target_lang)
        image_file = cls.generate_image(word)
        examples_count = random.randint(settings.content.min_examples, settings.content.max_examples)
        examples = cls.generate_examples(word, target_lang, native_lang, examples_count, user_examples)

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
