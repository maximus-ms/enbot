"""Configuration settings for the bot."""
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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
    file: Optional[str] = os.getenv("LOG_FILE")


@dataclass
class BotSettings:
    """Bot configuration settings."""
    token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_ids: list[int] = [
        int(id_) for id_ in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if id_
    ]
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


@dataclass
class NotificationSettings:
    """Notification settings."""
    daily_reminder_time: str = os.getenv("DAILY_REMINDER_TIME", "09:00")
    review_reminder_interval: int = int(os.getenv("REVIEW_REMINDER_INTERVAL", "24"))
    achievement_check_interval: int = int(os.getenv("ACHIEVEMENT_CHECK_INTERVAL", "24"))
    streak_check_interval: int = int(os.getenv("STREAK_CHECK_INTERVAL", "24"))


@dataclass
class Settings:
    """Main settings class that combines all configuration settings."""
    database: DatabaseSettings = DatabaseSettings()
    logging: LoggingSettings = LoggingSettings()
    bot: BotSettings = BotSettings()
    content: ContentSettings = ContentSettings()
    learning: LearningSettings = LearningSettings()
    notification: NotificationSettings = NotificationSettings()

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