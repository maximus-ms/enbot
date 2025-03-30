"""Tests for the main application."""
import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from telegram import Bot, User
from telegram.ext import Application

from enbot.app import EnBot


@pytest.fixture
async def bot() -> EnBot:
    """Create a bot instance with mocked dependencies."""
    # Create mock application with async methods
    mock_app = AsyncMock()
    mock_app.initialize = AsyncMock()
    mock_app.start = AsyncMock()
    mock_app.updater = AsyncMock()
    mock_app.updater.start_polling = AsyncMock()
    mock_app.stop = AsyncMock()
    mock_app.shutdown = AsyncMock()
    mock_app.add_handler = MagicMock()
    mock_app.bot = MagicMock()

    # Create mock builder
    mock_builder = MagicMock()
    mock_builder.token.return_value.build.return_value = mock_app

    # Create mock scheduler
    mock_scheduler = AsyncMock()
    mock_scheduler.start = AsyncMock()
    mock_scheduler.stop = AsyncMock()

    # Create patches
    patches = [
        patch("telegram.ext.Application.builder", return_value=mock_builder),
        patch("enbot.app.SchedulerService", return_value=mock_scheduler)
    ]

    # Start patches
    for p in patches:
        p.start()

    # Create bot instance
    bot = EnBot()

    yield bot

    # Cleanup
    for p in patches:
        p.stop()


@pytest.mark.asyncio
async def test_start(bot: EnBot) -> None:
    """Test starting the bot."""
    async for bot in bot:
        await bot.start()

        # Verify bot state
        assert bot.running
        assert bot.application is not None
        assert bot.scheduler is not None

        # Cleanup
        await bot.stop()


@pytest.mark.asyncio
async def test_stop(bot: EnBot) -> None:
    """Test stopping the bot."""
    async for bot in bot:
        await bot.start()
        await bot.stop()

        # Verify bot state
        assert not bot.running
        assert bot.application is None
        assert bot.scheduler is None


@pytest.mark.asyncio
async def test_start_when_already_running(bot: EnBot) -> None:
    """Test starting the bot when it's already running."""
    async for bot in bot:
        await bot.start()
        await bot.start()  # Should not raise or cause issues

        # Cleanup
        await bot.stop()


@pytest.mark.asyncio
async def test_stop_when_not_running(bot: EnBot) -> None:
    """Test stopping the bot when it's not running."""
    async for bot in bot:
        await bot.stop()  # Should not raise or cause issues


@pytest.mark.asyncio
async def test_error_handling(bot: EnBot) -> None:
    """Test error handling during start and stop."""
    async for bot in bot:
        await bot.start()

        # Simulate errors during stop
        bot.application.stop.side_effect = Exception("Test error")
        bot.application.shutdown.side_effect = Exception("Test error")
        bot.scheduler.stop.side_effect = Exception("Test error")

        # Should handle errors gracefully
        with pytest.raises(Exception) as exc_info:
            await bot.stop()
        assert str(exc_info.value) == "Test error"

        # Verify bot state
        assert not bot.running
        assert bot.application is None
        assert bot.scheduler is None


@pytest.mark.asyncio
async def test_run(bot: EnBot) -> None:
    """Test running the bot."""
    async for bot in bot:
        await bot.start()

        # Verify bot state
        assert bot.running
        assert bot.application is not None
        assert bot.scheduler is not None

        # Cleanup
        await bot.stop()


@pytest.mark.asyncio
async def test_run_loop(bot: EnBot) -> None:
    """Test running the bot in an event loop."""
    async for bot in bot:
        # Start the bot
        await bot.start()

        # Verify bot state
        assert bot.running
        assert bot.application is not None
        assert bot.scheduler is not None

        # Verify no messages were sent
        bot.application.bot.send_message.assert_not_called()

        # Cleanup
        await bot.stop()


if __name__ == "__main__":
    pytest.main([__file__]) 