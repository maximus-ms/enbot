"""Main Telegram bot module."""
import logging
from datetime import datetime
from typing import Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from enbot.config import settings
from enbot.models.base import SessionLocal
from enbot.services.learning_service import LearningService
from enbot.services.user_service import UserService

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
(
    MAIN_MENU,
    LEARNING,
    SETTINGS,
    ADD_WORDS,
    STATISTICS,
    LANGUAGE_SELECTION,
) = range(6)

# Button texts
START_LEARNING = "Start Learning"
ADD_NEW_WORDS = "Add New Words"
VIEW_STATISTICS = "View Statistics"
SETTINGS = "Settings"
BACK_TO_MENU = "Back to Menu"

# Settings options
CHANGE_LANGUAGE = "Change Language"
DAILY_GOALS = "Daily Goals"
NOTIFICATIONS = "Notifications"


async def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and show main menu."""
    user = update.effective_user
    db = SessionLocal()
    
    try:
        user_service = UserService(db)
        user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
        )
        
        keyboard = [
            [InlineKeyboardButton(START_LEARNING, callback_data="start_learning")],
            [InlineKeyboardButton(ADD_NEW_WORDS, callback_data="add_words")],
            [InlineKeyboardButton(VIEW_STATISTICS, callback_data="statistics")],
            [InlineKeyboardButton(SETTINGS, callback_data="settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Welcome to EnBot, {user.first_name}! 👋\n\n"
            "I'll help you learn English vocabulary effectively.\n"
            "What would you like to do?",
            reply_markup=reply_markup,
        )
        
        return MAIN_MENU
        
    finally:
        db.close()


async def handle_callback(update: Update, context: CallbackContext) -> int:
    """Handle callback queries from inline keyboard."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_learning":
        return await start_learning(update, context)
    elif query.data == "add_words":
        return await add_words(update, context)
    elif query.data == "statistics":
        return await show_statistics(update, context)
    elif query.data == "settings":
        return await show_settings(update, context)
    elif query.data == "back_to_menu":
        return await start(update, context)
    elif query.data.startswith("language_"):
        return await handle_language_selection(update, context)
    
    return MAIN_MENU


async def start_learning(update: Update, context: CallbackContext) -> int:
    """Start a learning session."""
    query = update.callback_query
    user = query.from_user
    db = SessionLocal()
    
    try:
        learning_service = LearningService(db)
        user_service = UserService(db)
        
        # Get or create active cycle
        cycle = learning_service.get_active_cycle(user.id)
        if not cycle:
            cycle = learning_service.create_new_cycle(user.id)
        
        # Get words for learning
        words = learning_service.get_words_for_cycle(cycle.id)
        if not words:
            await query.edit_message_text(
                "No words available for learning. Add some words first!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
                ]),
            )
            return MAIN_MENU
        
        # Show first word
        word = words[0]
        keyboard = [
            [
                InlineKeyboardButton("Show Translation", callback_data=f"show_translation_{word.id}"),
                InlineKeyboardButton("Show Examples", callback_data=f"show_examples_{word.id}"),
            ],
            [
                InlineKeyboardButton("I Know This", callback_data=f"know_word_{word.id}"),
                InlineKeyboardButton("I Don't Know", callback_data=f"dont_know_{word.id}"),
            ],
            [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
        ]
        
        await query.edit_message_text(
            f"Let's learn: {word.text}\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        return LEARNING
        
    finally:
        db.close()


async def add_words(update: Update, context: CallbackContext) -> int:
    """Start adding new words."""
    query = update.callback_query
    
    await query.edit_message_text(
        "Please enter words to add, one per line.\n"
        "For example:\n"
        "hello\n"
        "world\n"
        "python",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
        ]),
    )
    
    return ADD_WORDS


async def handle_add_words(update: Update, context: CallbackContext) -> int:
    """Handle adding new words."""
    user = update.effective_user
    db = SessionLocal()
    
    try:
        user_service = UserService(db)
        words = [word.strip() for word in update.message.text.split("\n") if word.strip()]
        
        if not words:
            await update.message.reply_text(
                "No valid words provided. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
                ]),
            )
            return ADD_WORDS
        
        added_words = user_service.add_words(user.id, words)
        
        await update.message.reply_text(
            f"Successfully added {len(added_words)} words!\n"
            "Would you like to add more words?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Add More", callback_data="add_words")],
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
            ]),
        )
        
        return MAIN_MENU
        
    finally:
        db.close()


async def show_statistics(update: Update, context: CallbackContext) -> int:
    """Show user statistics."""
    query = update.callback_query
    user = query.from_user
    db = SessionLocal()
    
    try:
        user_service = UserService(db)
        stats = user_service.get_user_statistics(user.id)
        
        message = (
            "📊 Your Learning Statistics (Last 30 Days):\n\n"
            f"Total Words Learned: {stats['total_words']}\n"
            f"Total Time Spent: {stats['total_time_minutes']:.1f} minutes\n"
            f"Total Learning Cycles: {stats['total_cycles']}\n"
            f"Average Words per Cycle: {stats['average_words_per_cycle']:.1f}\n"
            f"Average Time per Cycle: {stats['average_time_per_cycle']:.1f} minutes\n"
        )
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        
        return MAIN_MENU
        
    finally:
        db.close()


async def show_settings(update: Update, context: CallbackContext) -> int:
    """Show settings menu."""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton(CHANGE_LANGUAGE, callback_data="change_language")],
        [InlineKeyboardButton(DAILY_GOALS, callback_data="daily_goals")],
        [InlineKeyboardButton(NOTIFICATIONS, callback_data="notifications")],
        [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
    ]
    
    await query.edit_message_text(
        "⚙️ Settings\n\n"
        "What would you like to change?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    
    return SETTINGS


async def handle_language_selection(update: Update, context: CallbackContext) -> int:
    """Handle language selection."""
    query = update.callback_query
    user = query.from_user
    db = SessionLocal()
    
    try:
        user_service = UserService(db)
        language = query.data.split("_")[1]
        
        if query.data.startswith("native_"):
            user_service.update_user_settings(user.id, native_language=language)
        else:
            user_service.update_user_settings(user.id, target_language=language)
        
        await query.edit_message_text(
            "Language settings updated successfully!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        
        return MAIN_MENU
        
    finally:
        db.close()


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
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
    
    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    main() 