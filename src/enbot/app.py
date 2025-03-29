"""Main application entry point."""
import asyncio
import logging
import signal
from typing import Optional

from telegram import Bot
from telegram.ext import Application

from enbot.config import settings
from enbot.models.base import init_db
from enbot.services.scheduler_service import SchedulerService
from enbot.bot import (
    start,
    handle_callback,
    start_learning,
    add_words,
    handle_add_words,
    show_statistics,
    show_settings,
    handle_language_selection,
    MAIN_MENU,
    LEARNING,
    ADD_WORDS,
    SETTINGS,
    STATISTICS,
    LANGUAGE_SELECTION,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class EnBot:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.application: Optional[Application] = None
        self.scheduler: Optional[SchedulerService] = None
        self.running = False

    async def start(self) -> None:
        """Start the application."""
        if self.running:
            return

        try:
            # Initialize database
            init_db()
            logger.info("Database initialized")

            # Create application
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
            logger.info("Application created")

            # Add conversation handler
            self.application.add_handler(
                ConversationHandler(
                    entry_points=[CommandHandler("start", start)],
                    states={
                        MAIN_MENU: [
                            CallbackQueryHandler(handle_callback),
                        ],
                        LEARNING: [
                            CallbackQueryHandler(handle_callback),
                        ],
                        ADD_WORDS: [
                            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_words),
                            CallbackQueryHandler(handle_callback),
                        ],
                        SETTINGS: [
                            CallbackQueryHandler(handle_callback),
                        ],
                        STATISTICS: [
                            CallbackQueryHandler(handle_callback),
                        ],
                        LANGUAGE_SELECTION: [
                            CallbackQueryHandler(handle_callback),
                        ],
                    },
                    fallbacks=[CommandHandler("start", start)],
                )
            )
            logger.info("Handlers added")

            # Create scheduler service
            self.scheduler = SchedulerService(self.application.bot)
            await self.scheduler.start()
            logger.info("Scheduler service started")

            # Start application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Application started")

            self.running = True

        except Exception as e:
            logger.error("Failed to start application: %s", str(e))
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the application."""
        if not self.running:
            return

        try:
            # Stop scheduler service
            if self.scheduler:
                await self.scheduler.stop()
                logger.info("Scheduler service stopped")

            # Stop application
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Application stopped")

            self.running = False

        except Exception as e:
            logger.error("Error while stopping application: %s", str(e))
            raise

    def run(self) -> None:
        """Run the application."""
        # Create event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create bot instance
        bot = EnBot()

        # Handle signals
        def signal_handler(signum, frame):
            logger.info("Received signal %d", signum)
            loop.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Start bot
            loop.run_until_complete(bot.start())

            # Run event loop
            loop.run_forever()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            # Stop bot
            loop.run_until_complete(bot.stop())
            loop.close()


def main() -> None:
    """Main entry point."""
    bot = EnBot()
    bot.run()


if __name__ == "__main__":
    main() 