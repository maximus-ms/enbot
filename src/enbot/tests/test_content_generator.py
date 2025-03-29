"""Tests for content generation service."""
from pathlib import Path

import pytest

from enbot.services.content_generator import ContentGenerator
from enbot.models.models import Example


def test_generate_translation() -> None:
    """Test translation generation."""
    word = "hello"
    translation = ContentGenerator.generate_translation(word, "uk")
    assert isinstance(translation, str)
    assert len(translation) > 0


def test_generate_transcription() -> None:
    """Test transcription generation."""
    word = "hello"
    transcription = ContentGenerator.generate_transcription(word)
    assert isinstance(transcription, str)
    assert len(transcription) > 0


def test_generate_pronunciation() -> None:
    """Test pronunciation file path generation."""
    word = "hello world"
    pronunciation_file = ContentGenerator.generate_pronunciation(word)
    assert isinstance(pronunciation_file, str)
    assert pronunciation_file.endswith(".mp3")
    assert "hello_world" in pronunciation_file


def test_generate_image() -> None:
    """Test image file path generation."""
    word = "hello world"
    image_file = ContentGenerator.generate_image(word)
    assert isinstance(image_file, str)
    assert image_file.endswith(".jpg")
    assert "hello_world" in image_file


def test_generate_examples() -> None:
    """Test example generation."""
    word = "hello"
    translation = "привіт"
    examples = ContentGenerator.generate_examples(word, translation, count=3)
    
    assert len(examples) == 3
    for example in examples:
        assert isinstance(example, Example)
        assert isinstance(example.sentence, str)
        assert isinstance(example.translation, str)
        assert example.is_good is True


def test_generate_word_content() -> None:
    """Test complete word content generation."""
    word = "hello"
    target_lang = "en"
    native_lang = "uk"
    
    word_obj, examples = ContentGenerator.generate_word_content(
        word, target_lang, native_lang
    )
    
    assert word_obj.text == word
    assert word_obj.language_pair == f"{target_lang}-{native_lang}"
    assert len(examples) > 0
    assert all(isinstance(example, Example) for example in examples)


if __name__ == "__main__":
    pytest.main([__file__]) 