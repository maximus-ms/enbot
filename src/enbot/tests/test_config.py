"""Tests for configuration settings."""
import os
from pathlib import Path

import pytest

from enbot.config import settings


def test_base_directories_exist():
    """Test that all required directories exist."""
    from enbot.config import (
        BASE_DIR,
        DATA_DIR,
        DICTIONARIES_DIR,
        MEDIA_DIR,
        PRONUNCIATIONS_DIR,
        IMAGES_DIR,
    )
    
    assert BASE_DIR.exists()
    assert DATA_DIR.exists()
    assert DICTIONARIES_DIR.exists()
    assert MEDIA_DIR.exists()
    assert PRONUNCIATIONS_DIR.exists()
    assert IMAGES_DIR.exists()


def test_settings_defaults():
    """Test default settings values."""
    # Database settings
    # assert settings.database.url == "sqlite:///enbot.db"
    # assert settings.database.echo is False

    # Logging settings
    # assert settings.logging.level == "INFO"
    # assert settings.logging.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    # assert settings.logging.file is None

    # Bot settings
    assert settings.bot.token is not None
    assert settings.bot.admin_ids is not None
    assert settings.bot.webhook_url is not None
    assert isinstance(settings.bot.webhook_port, int)

    # Content settings
    assert settings.content.max_examples == 3
    assert settings.content.min_examples == 1
    assert settings.content.max_synonyms == 3
    assert settings.content.min_synonyms == 1
    assert settings.content.max_antonyms == 2
    assert settings.content.min_antonyms == 1

    # Learning settings
    assert settings.learning.words_per_cycle == 10
    assert settings.learning.new_words_ratio == 0.3
    assert settings.learning.min_priority == 1
    assert settings.learning.max_priority == 5
    assert settings.learning.default_priority == 3

    # Notification settings
    assert settings.notification.daily_reminder_time == "09:00"
    assert settings.notification.review_reminder_interval == 24
    assert settings.notification.achievement_check_interval == 24
    assert settings.notification.streak_check_interval == 24


# def test_settings_from_env():
#     """Test that settings can be overridden by environment variables."""
#     test_token = "test_token_123"
#     os.environ["TELEGRAM_BOT_TOKEN"] = test_token
    
#     # Reload settings to pick up environment variable
#     from enbot.config import Settings
#     test_settings = Settings()
    
#     assert test_settings.bot.token == test_token
    
#     # Clean up
#     del os.environ["TELEGRAM_BOT_TOKEN"]


if __name__ == "__main__":
    pytest.main([__file__])
