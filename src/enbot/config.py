"""Configuration settings for the bot."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Define base directory
BASE_DIR = Path(__file__).parent.parent.parent

# Load environment variables from .env file
env_file = ".env.test" if os.getenv("ENV") == "test" else ".env"
load_dotenv(env_file)


# Define data directories from environment variables
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DICTIONARIES_DIR = DATA_DIR / "dictionaries"
MEDIA_DIR = DATA_DIR / "media"
PRONUNCIATIONS_DIR = MEDIA_DIR / "pronunciations"
IMAGES_DIR = MEDIA_DIR / "images"

# Learning settings
REPETITION_INTERVALS = [1, 3, 7, 14, 30]  # days between reviews
REPETITION_HISTORY_PERCENTAGE = 0.3  # 30% of words in cycle should be from history


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    directories = [
        DATA_DIR,
        DICTIONARIES_DIR,
        MEDIA_DIR,
        PRONUNCIATIONS_DIR,
        IMAGES_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


@dataclass
class PathSettings:
    """Path configuration settings."""
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    dictionaries_dir: Path = DICTIONARIES_DIR
    media_dir: Path = MEDIA_DIR
    pronunciations_dir: Path = PRONUNCIATIONS_DIR
    images_dir: Path = IMAGES_DIR


@dataclass
class DatabaseSettings:
    """Database configuration settings."""
    url: str = os.getenv("DATABASE_URL", "sqlite:///enbot.db")
    echo: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"


@dataclass
class LoggingSettings:
    """Logging configuration settings."""
    level: str = os.getenv("LOG_LEVEL", "INFO")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    dir: Optional[str] = os.getenv("LOG_DIR", None)


def get_admin_ids() -> list[int]:
    """Get admin IDs from environment variable."""
    return [int(id_) for id_ in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if id_]


@dataclass
class BotSettings:
    """Bot configuration settings."""
    token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_ids: list[int] = field(default_factory=get_admin_ids)
    webhook_url: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL")
    webhook_port: int = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "8443"))


@dataclass
class ContentSettings:
    """Content generation settings."""
    max_examples: int = int(os.getenv("MAX_EXAMPLES", "3"))
    min_examples: int = int(os.getenv("MIN_EXAMPLES", "1"))
    max_synonyms: int = int(os.getenv("MAX_SYNONYMS", "3"))
    min_synonyms: int = int(os.getenv("MIN_SYNONYMS", "1"))
    max_antonyms: int = int(os.getenv("MAX_ANTONYMS", "2"))
    min_antonyms: int = int(os.getenv("MIN_ANTONYMS", "1"))


@dataclass
class LearningSettings:
    """Learning process settings."""
    words_per_cycle: int = int(os.getenv("WORDS_PER_CYCLE", "10"))
    new_words_ratio: float = float(os.getenv("NEW_WORDS_RATIO", "0.3"))
    min_priority: int = int(os.getenv("MIN_PRIORITY", "1"))
    max_priority: int = int(os.getenv("MAX_PRIORITY", "5"))
    default_priority: int = int(os.getenv("DEFAULT_PRIORITY", "3"))
    repetition_intervals: list[int] = field(default_factory=lambda: REPETITION_INTERVALS)
    repetition_history_percentage: float = REPETITION_HISTORY_PERCENTAGE


@dataclass
class NotificationSettings:
    """Notification settings."""
    daily_reminder_time: str = os.getenv("DAILY_REMINDER_TIME", "09:00")
    review_reminder_interval: int = int(os.getenv("REVIEW_REMINDER_INTERVAL", "24"))
    achievement_check_interval: int = int(os.getenv("ACHIEVEMENT_CHECK_INTERVAL", "24"))
    streak_check_interval: int = int(os.getenv("STREAK_CHECK_INTERVAL", "24"))


def get_path_settings() -> PathSettings:
    """Get path settings."""
    return PathSettings()


def get_database_settings() -> DatabaseSettings:
    """Get database settings."""
    return DatabaseSettings()


def get_logging_settings() -> LoggingSettings:
    """Get logging settings."""
    return LoggingSettings()


def get_bot_settings() -> BotSettings:
    """Get bot settings."""
    return BotSettings()


def get_content_settings() -> ContentSettings:
    """Get content settings."""
    return ContentSettings()


def get_learning_settings() -> LearningSettings:
    """Get learning settings."""
    return LearningSettings()


def get_notification_settings() -> NotificationSettings:
    """Get notification settings."""
    return NotificationSettings()


@dataclass
class Settings:
    """Main settings class that combines all configuration settings."""
    paths: PathSettings = field(default_factory=get_path_settings)
    database: DatabaseSettings = field(default_factory=get_database_settings)
    logging: LoggingSettings = field(default_factory=get_logging_settings)
    bot: BotSettings = field(default_factory=get_bot_settings)
    content: ContentSettings = field(default_factory=get_content_settings)
    learning: LearningSettings = field(default_factory=get_learning_settings)
    notification: NotificationSettings = field(default_factory=get_notification_settings)

    def validate(self) -> None:
        """Validate settings and raise ValueError if invalid."""
        if not self.bot.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        if self.learning.new_words_ratio < 0 or self.learning.new_words_ratio > 1:
            raise ValueError("NEW_WORDS_RATIO must be between 0 and 1")

        if self.learning.words_per_cycle < 1:
            raise ValueError("WORDS_PER_CYCLE must be positive")

        if self.learning.min_priority > self.learning.max_priority:
            raise ValueError("MIN_PRIORITY cannot be greater than MAX_PRIORITY")

        if self.learning.default_priority < self.learning.min_priority or \
           self.learning.default_priority > self.learning.max_priority:
            raise ValueError("DEFAULT_PRIORITY must be between MIN_PRIORITY and MAX_PRIORITY")


# Create global settings instance
settings = Settings()
settings.validate() 