"""Service for managing scheduled tasks and notifications."""
import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Callable, Dict, Any

from sqlalchemy.orm import Session
from telegram import Bot

from enbot.models.base import SessionLocal
from enbot.models.models import User
from enbot.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled tasks and notifications."""

    def __init__(self, bot: Bot, db: Session):
        """Initialize the service with a Telegram bot instance and database session."""
        self.bot = bot
        self.db = db
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self.notification_service = NotificationService(db)

    async def start(self) -> None:
        """Start the scheduler service."""
        if self.running:
            return

        self.running = True
        logger.info("Starting scheduler service...")

        # Start daily notification task
        self.tasks["daily_notifications"] = asyncio.create_task(
            self._run_daily_notifications()
        )

        # Start review reminder task
        self.tasks["review_reminders"] = asyncio.create_task(
            self._run_review_reminders()
        )

        # Start achievement check task
        self.tasks["achievement_checks"] = asyncio.create_task(
            self._run_achievement_checks()
        )

        # Start streak check task
        self.tasks["streak_checks"] = asyncio.create_task(
            self._run_streak_checks()
        )

    async def stop(self) -> None:
        """Stop the scheduler service."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping scheduler service...")

        # Cancel all tasks
        for task in self.tasks.values():
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()

    async def _run_daily_notifications(self) -> None:
        """Run daily notification task."""
        while self.running:
            try:
                # Get current hour
                current_hour = datetime.now(UTC).hour

                # Get users for notification
                users = self.notification_service.get_users_for_notification()

                # Send notifications
                for user in users:
                    try:
                        # Get message
                        message = self.notification_service.get_daily_reminder_message(user)

                        # Send message
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode="HTML",
                        )

                        # Update last notification time
                        self.notification_service.update_last_notification_time(user)

                        # Log success
                        logger.info(
                            "Sent daily notification to user %s (ID: %d)",
                            user.username,
                            user.telegram_id,
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to send daily notification to user %s (ID: %d): %s",
                            user.username,
                            user.telegram_id,
                            str(e),
                        )

                # Wait until next hour
                await asyncio.sleep(3600)  # 1 hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in daily notification task: %s", str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _run_review_reminders(self) -> None:
        """Run review reminder task."""
        while self.running:
            try:
                # Get all users with notifications enabled
                users = (
                    self.db.query(User)
                    .filter(User.notifications_enabled == True)
                    .all()
                )

                # Check each user
                for user in users:
                    try:
                        # Check if should send reminder
                        if not self.notification_service.should_send_review_reminder(user):
                            continue

                        # Get message
                        message = self.notification_service.get_review_reminder_message(user)
                        if not message:
                            continue

                        # Send message
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode="HTML",
                        )

                        # Update last notification time
                        self.notification_service.update_last_notification_time(user)

                        # Log success
                        logger.info(
                            "Sent review reminder to user %s (ID: %d)",
                            user.username,
                            user.telegram_id,
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to send review reminder to user %s (ID: %d): %s",
                            user.username,
                            user.telegram_id,
                            str(e),
                        )

                # Wait 30 minutes before next check
                await asyncio.sleep(1800)  # 30 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in review reminder task: %s", str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _run_achievement_checks(self) -> None:
        """Run achievement check task."""
        while self.running:
            try:
                # Get all users
                users = self.db.query(User).all()

                # Check each user
                for user in users:
                    try:
                        # Get achievement message
                        message = self.notification_service.get_achievement_message(user)
                        if not message:
                            continue

                        # Send message
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode="HTML",
                        )

                        # Log success
                        logger.info(
                            "Sent achievement message to user %s (ID: %d)",
                            user.username,
                            user.telegram_id,
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to send achievement message to user %s (ID: %d): %s",
                            user.username,
                            user.telegram_id,
                            str(e),
                        )

                # Wait 1 hour before next check
                await asyncio.sleep(3600)  # 1 hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in achievement check task: %s", str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _run_streak_checks(self) -> None:
        """Run streak check task."""
        while self.running:
            try:
                # Get all users
                users = self.db.query(User).all()

                # Check each user
                for user in users:
                    try:
                        # Get streak message
                        message = self.notification_service.get_streak_message(user)
                        if not message:
                            continue

                        # Send message
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode="HTML",
                        )

                        # Log success
                        logger.info(
                            "Sent streak message to user %s (ID: %d)",
                            user.username,
                            user.telegram_id,
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to send streak message to user %s (ID: %d): %s",
                            user.username,
                            user.telegram_id,
                            str(e),
                        )

                # Wait 1 hour before next check
                await asyncio.sleep(3600)  # 1 hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in streak check task: %s", str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    def schedule_task(
        self,
        name: str,
        coro: Callable,
        interval: float,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Schedule a new task."""
        if name in self.tasks:
            logger.warning("Task %s already exists", name)
            return

        async def run_task() -> None:
            while self.running:
                try:
                    await coro(*args, **kwargs)
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in task %s: %s", name, str(e))
                    await asyncio.sleep(60)  # Wait 1 minute before retrying

        self.tasks[name] = asyncio.create_task(run_task())
        logger.info("Scheduled task: %s", name)

    def cancel_task(self, name: str) -> None:
        """Cancel a scheduled task."""
        if name not in self.tasks:
            logger.warning("Task %s does not exist", name)
            return

        self.tasks[name].cancel()
        del self.tasks[name]
        logger.info("Cancelled task: %s", name) 