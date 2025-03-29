"""Logging configuration for the bot."""
import logging
import logging.handlers
import os
from pathlib import Path

from enbot.config import settings


def setup_logging() -> None:
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    if settings.logging.file:
        log_dir = Path(settings.logging.file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.logging.level)

    # Create formatters
    formatter = logging.Formatter(settings.logging.format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if log file is specified
    if settings.logging.file:
        file_handler = logging.handlers.RotatingFileHandler(
            settings.logging.file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set logging levels for third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log startup message
    logging.info("Logging configured successfully")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name) 