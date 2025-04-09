"""Main application entry point."""
import asyncio
import logging
import signal
import sys
from typing import Optional
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

# Suppress the warning about CallbackQueryHandler and per_message
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

from telegram import Bot
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from enbot.config import settings
from enbot.models.base import init_db, SessionLocal
from enbot.services.scheduler_service import SchedulerService
from enbot.bot import (
    handle_start,
    handle_callback,
    handle_message,
    handle_add_words,
    handle_learning_response,
    handle_admin_menu_admin_add_delete,
    MAIN_MENU,
    ADDING_WORDS,
    LEARNING,
    ADMIN_MENU_ADMIN_ADD_DELETE,
)


class EnBot:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.application: Optional[Application] = None
        self.scheduler: Optional[SchedulerService] = None
        self.running = False
        self.db = None
        self.logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start the application."""
        if self.running:
            return

        try:
            # Initialize database
            init_db()
            self.db = SessionLocal()
            self.logger.info("Database initialized")

            # Create application
            self.application = Application.builder().token(settings.bot.token).build()
            self.logger.info("Application created")

            # Set up error notifications
            from enbot.bot import setup_admin_notifications
            setup_admin_notifications(self.application, settings.logging.admin_notification_level)

            # Create conversation handler for both messages and callbacks
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler("start", handle_start)],
                states={
                    MAIN_MENU: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
                        CallbackQueryHandler(handle_callback),
                    ],
                    ADDING_WORDS: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_words),
                        CallbackQueryHandler(handle_callback),
                    ],
                    LEARNING: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_learning_response),
                        CallbackQueryHandler(handle_learning_response),
                    ],
                    ADMIN_MENU_ADMIN_ADD_DELETE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_menu_admin_add_delete),
                        CallbackQueryHandler(handle_admin_menu_admin_add_delete),
                    ],
                },
                fallbacks=[CommandHandler("start", handle_start)],
                per_message=False,
            )

            # Add conversation handler
            self.application.add_handler(conv_handler)
            self.logger.info("Handlers added")

            # Create scheduler service
            self.scheduler = SchedulerService(self.application.bot, self.db)
            await self.scheduler.start()
            self.logger.info("Scheduler service started")

            # Start application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            self.logger.info("Application started")

            self.running = True

        except Exception as e:
            self.logger.error("Failed to start application: %s", str(e))
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
                self.scheduler = None
                self.logger.info("Scheduler service stopped")

            # Stop application
            if self.application:
                from enbot.bot import disable_admin_notifications
                disable_admin_notifications()
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                self.application = None
                self.logger.info("Application stopped")

            # Close database session
            if self.db:
                self.db.close()
                self.logger.info("Database session closed")

            self.running = False

        except Exception as e:
            self.logger.error("Error while stopping application: %s", str(e))
            self.running = False
            self.application = None
            self.scheduler = None
            raise

    def run(self) -> None:
        """Run the application."""
        # Create event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Handle signals
        def signal_handler(signum, frame):
            """Handle signals like SIGINT (Ctrl+C)."""
            print()  # Print a newline to ensure log messages start on a new line
            self.logger.info(f"Received signal {signum}. Shutting down...")
            
            # Save cycle service state
            from enbot.services.cycle_service import CycleService
            from enbot.services.learning_service import LearningService
            from enbot.database import SessionLocal
            
            db = SessionLocal()
            try:
                learning_service = LearningService(db)
                cycle_service = CycleService(learning_service)
                cycle_service.save_state()
                self.logger.info("Cycle service state saved successfully")
            except Exception as e:
                self.logger.error(f"Error saving cycle service state: {e}")
            finally:
                db.close()
            
            # Exit gracefully
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Start bot
            loop.run_until_complete(self.start())

            # Run event loop
            loop.run_forever()

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            # Stop bot
            loop.run_until_complete(self.stop())
            loop.close()


def main() -> None:
    """Main entry point."""
    bot = EnBot()
    bot.run()


if __name__ == "__main__":
    main() 