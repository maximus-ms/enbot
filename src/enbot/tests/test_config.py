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
    assert settings.DEFAULT_CYCLE_SIZE == 10
    assert settings.REPETITION_HISTORY_PERCENTAGE == 0.7
    assert settings.DEFAULT_DAY_START_HOUR == 3
    assert settings.MAX_PRIORITY_LEVEL == 10
    assert settings.REPETITION_PRIORITY_LEVEL == 11
    assert settings.PRIORITY_COOLDOWN_DAYS == 30
    assert settings.MAX_EXAMPLES_PER_WORD == 5
    assert settings.IMAGE_SIZE == {"width": 320, "height": 240}
    assert settings.REPETITION_INTERVALS == [1, 3, 5, 10, 30]


def test_settings_from_env():
    """Test that settings can be overridden by environment variables."""
    test_token = "test_token_123"
    os.environ["TELEGRAM_BOT_TOKEN"] = test_token
    
    # Reload settings to pick up environment variable
    from enbot.config import Settings
    test_settings = Settings()
    
    assert test_settings.TELEGRAM_BOT_TOKEN == test_token
    
    # Clean up
    del os.environ["TELEGRAM_BOT_TOKEN"]


if __name__ == "__main__":
    pytest.main([__file__]) 