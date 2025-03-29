"""Tests for main application."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Bot
from telegram.ext import Application

from enbot.app import EnBot
from enbot.config import settings


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock bot."""
    bot = MagicMock(spec=Bot)
    bot.get_me = AsyncMock()
    return bot


@pytest.fixture
def mock_application(mock_bot: MagicMock) -> MagicMock:
    """Create a mock application."""
    app = MagicMock(spec=Application)
    app.bot = mock_bot
    app.initialize = AsyncMock()
    app.start = AsyncMock()
    app.stop = AsyncMock()
    app.shutdown = AsyncMock()
    app.updater = MagicMock()
    app.updater.start_polling = AsyncMock()
    app.updater.stop = AsyncMock()
    app.add_handler = MagicMock()
    return app


@pytest.fixture
def mock_scheduler() -> MagicMock:
    """Create a mock scheduler service."""
    scheduler = MagicMock()
    scheduler.start = AsyncMock()
    scheduler.stop = AsyncMock()
    return scheduler


@pytest.fixture
def mock_builder(mock_application: MagicMock) -> MagicMock:
    """Create a mock application builder."""
    builder = MagicMock()
    builder.token.return_value.build.return_value = mock_application
    return builder


@pytest.fixture
def bot(mock_builder: MagicMock, mock_scheduler: MagicMock) -> EnBot:
    """Create a bot instance with mocked dependencies."""
    with patch("enbot.app.Application.builder", return_value=mock_builder), \
         patch("enbot.app.SchedulerService", return_value=mock_scheduler):
        return EnBot()


@pytest.mark.asyncio
async def test_start(bot: EnBot) -> None:
    """Test starting the bot."""
    # Start bot
    await bot.start()

    # Check application was initialized
    assert bot.application is not None
    bot.application.initialize.assert_called_once()
    bot.application.start.assert_called_once()
    bot.application.updater.start_polling.assert_called_once()

    # Check scheduler was started
    assert bot.scheduler is not None
    bot.scheduler.start.assert_called_once()

    # Check running state
    assert bot.running is True


@pytest.mark.asyncio
async def test_stop(bot: EnBot) -> None:
    """Test stopping the bot."""
    # Start bot first
    await bot.start()

    # Stop bot
    await bot.stop()

    # Check application was stopped
    bot.application.updater.stop.assert_called_once()
    bot.application.stop.assert_called_once()
    bot.application.shutdown.assert_called_once()

    # Check scheduler was stopped
    bot.scheduler.stop.assert_called_once()

    # Check running state
    assert bot.running is False


@pytest.mark.asyncio
async def test_start_when_already_running(bot: EnBot) -> None:
    """Test starting the bot when it's already running."""
    # Start bot first
    await bot.start()

    # Try to start again
    await bot.start()

    # Check application was only initialized once
    bot.application.initialize.assert_called_once()
    bot.application.start.assert_called_once()
    bot.application.updater.start_polling.assert_called_once()


@pytest.mark.asyncio
async def test_stop_when_not_running(bot: EnBot) -> None:
    """Test stopping the bot when it's not running."""
    # Stop bot without starting
    await bot.stop()

    # Check nothing was called
    if bot.application:
        bot.application.updater.stop.assert_not_called()
        bot.application.stop.assert_not_called()
        bot.application.shutdown.assert_not_called()
    if bot.scheduler:
        bot.scheduler.stop.assert_not_called()


@pytest.mark.asyncio
async def test_error_handling(bot: EnBot) -> None:
    """Test error handling during start and stop."""
    await bot.start()  # Need to start first to create application
    
    # Make next initialize raise an exception
    bot.application.initialize.reset_mock(side_effect=True)
    bot.application.initialize.side_effect = Exception("Test error")

    # Try to start bot again
    with pytest.raises(Exception):
        await bot.start()

    # Check stop was called
    bot.application.updater.stop.assert_called_once()
    bot.application.stop.assert_called_once()
    bot.application.shutdown.assert_called_once()
    bot.scheduler.stop.assert_called_once()


def test_run(bot: EnBot) -> None:
    """Test running the bot."""
    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run bot
    with patch.object(loop, "run_forever") as mock_run_forever:
        mock_run_forever.side_effect = KeyboardInterrupt()
        bot.run()

    # Check application was started and stopped
    bot.application.initialize.assert_called_once()
    bot.application.start.assert_called_once()
    bot.application.updater.start_polling.assert_called_once()
    bot.application.updater.stop.assert_called_once()
    bot.application.stop.assert_called_once()
    bot.application.shutdown.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 