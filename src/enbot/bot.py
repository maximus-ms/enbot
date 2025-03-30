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
    ContextTypes,
)

from enbot.config import settings
from enbot.models.base import SessionLocal
from enbot.models.models import User, UserWord, CycleWord
from enbot.services.learning_service import LearningService
from enbot.services.user_service import UserService
from sqlalchemy import and_

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
BACK_TO_GOALS = "Back to Goals"
BACK_TO_SETTINGS = "Back to Settings"
BACK_TO_MENU = "Back to Menu"
# Settings options
# CHANGE_LANGUAGE = "Change Language"
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
        
        # Handle both initial command and callback queries
        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"Welcome to EnBot, {user.first_name}! 👋\n\n"
                "I'll help you learn English vocabulary effectively.\n"
                "What would you like to do?",
                reply_markup=reply_markup,
            )
        else:
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
    elif query.data == "daily_goals":
        return await handle_daily_goals(update, context)
    elif query.data == "daily_goals_words":
        return await handle_daily_goals_words(update, context)
    elif query.data == "daily_goals_time":
        return await handle_daily_goals_time(update, context)
    elif query.data.startswith("set_goal_"):
        return await handle_set_goal(update, context)
    elif query.data.startswith("know_"):
        return await handle_word_response(update, context, True)
    elif query.data.startswith("dont_know_"):
        return await handle_word_response(update, context, False)
    
    return MAIN_MENU


async def start_learning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a new learning cycle."""
    user = get_user_from_update(update)
    if not user:
        await update.callback_query.edit_message_text(
            "Please /start first to register.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        return MAIN_MENU

    db = SessionLocal()
    try:
        learning_service = LearningService(db)
        user_service = UserService(db)

        # Check if user has any words
        user_words = user_service.get_user_words(user.id)
        if not user_words:
            await update.callback_query.edit_message_text(
                "No words available for learning. Add some words first!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Words", callback_data="add_words")],
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
                ]),
            )
            return MAIN_MENU

        # Create a new cycle
        cycle = learning_service.create_new_cycle(user.id)

        # Get words for learning
        words = learning_service.get_words_for_cycle(user.id, settings.learning.words_per_cycle)
        if not words:
            await update.callback_query.edit_message_text(
                "No words available for learning. Add some words first!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Words", callback_data="add_words")],
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
                ]),
            )
            return MAIN_MENU

        # Add words to cycle
        cycle_words = learning_service.add_words_to_cycle(cycle.id, words)
        word = words[0].word
        example = word.examples[0] if word.examples else None

        # Show the first word
        keyboard = [
            [
                InlineKeyboardButton("✅ I know this", callback_data=f"know_{word.id}"),
                InlineKeyboardButton("❌ Don't know", callback_data=f"dont_know_{word.id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = f"Let's learn some words!\n\n" \
                 f"Word: {word.text}\n" \
                 f"Translation: {word.translation}"
        
        if example:
            message += f"\nExample: {example.sentence}"

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
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
    user = get_user_from_update(update)
    if not user:
        await update.message.reply_text("Please /start first to register.")
        return MAIN_MENU

    db = SessionLocal()
    try:
        user_service = UserService(db)
        
        # Split text by multiple separators (newline and semicolon)
        text = update.message.text
        words = []
        for line in text.split('\n'):
            # Split each line by semicolon and add non-empty words
            words.extend(word.strip() for word in line.split(';') if word.strip())
        
        if not words:
            await update.message.reply_text(
                "No valid words provided. Please try again.\n"
                "You can separate words by new lines or semicolons.\n"
                "Example:\n"
                "hello; world\n"
                "python; java",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
                ]),
            )
            return ADD_WORDS
        
        added_words = user_service.add_words(user.id, words)
        
        await update.message.reply_text(
            f"Successfully added {len(added_words)} word(s)!\n"
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
    user = get_user_from_update(update)
    if not user:
        await update.callback_query.edit_message_text(
            "Please /start first to register.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        return MAIN_MENU

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
        
        await update.callback_query.edit_message_text(
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
        # [InlineKeyboardButton(CHANGE_LANGUAGE, callback_data="change_language")],
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
    user = get_user_from_update(update)
    if not user:
        await update.callback_query.edit_message_text(
            "Please /start first to register.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        return MAIN_MENU

    db = SessionLocal()
    try:
        user_service = UserService(db)
        language = update.callback_query.data.split("_")[1]
        
        if update.callback_query.data.startswith("native_"):
            user_service.update_user_settings(user.id, native_language=language)
        else:
            user_service.update_user_settings(user.id, target_language=language)
        
        await update.callback_query.edit_message_text(
            "Language settings updated successfully!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        
        return MAIN_MENU
        
    finally:
        db.close()


async def handle_word_response(update: Update, context: CallbackContext, is_known: bool) -> int:
    """Handle user's response to a word (know/don't know)."""
    user = get_user_from_update(update)
    if not user:
        await update.callback_query.edit_message_text(
            "Please /start first to register.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        return MAIN_MENU

    db = SessionLocal()
    try:
        learning_service = LearningService(db)
        word_id = int(update.callback_query.data.split("_")[1])
        
        # Get the current cycle
        cycle = learning_service.get_active_cycle(user.id)
        if not cycle:
            await update.callback_query.edit_message_text(
                "No active learning cycle found. Please start learning again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
                ]),
            )
            return MAIN_MENU

        # Get the user_word_id for this word
        user_word = (
            db.query(UserWord)
            .filter(
                and_(
                    UserWord.user_id == user.id,
                    UserWord.word_id == word_id,
                )
            )
            .first()
        )
        if not user_word:
            await update.callback_query.edit_message_text(
                "Error: Word not found in your vocabulary.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
                ]),
            )
            return MAIN_MENU

        # Check if the word is in the current cycle
        cycle_word = (
            db.query(CycleWord)
            .filter(
                and_(
                    CycleWord.cycle_id == cycle.id,
                    CycleWord.user_word_id == user_word.id,
                )
            )
            .first()
        )
        if not cycle_word:
            await update.callback_query.edit_message_text(
                "Error: Word not found in current learning cycle.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
                ]),
            )
            return MAIN_MENU

        # Mark the word as learned if user knows it
        if is_known:
            learning_service.mark_word_as_learned(cycle.id, user_word.id, 0.0)  # Time spent is 0 for now

        # Get the next word
        words = learning_service.get_words_for_cycle(user.id, settings.learning.words_per_cycle)
        if not words:
            # No more words, complete the cycle
            learning_service.complete_cycle(cycle.id)
            await update.callback_query.edit_message_text(
                "🎉 Congratulations! You've completed this learning cycle!\n"
                "Would you like to start another one?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Start New Cycle", callback_data="start_learning")],
                    [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
                ]),
            )
            return MAIN_MENU

        # Show the next word
        word = words[0].word
        example = word.examples[0] if word.examples else None

        keyboard = [
            [
                InlineKeyboardButton("✅ I know this", callback_data=f"know_{word.id}"),
                InlineKeyboardButton("❌ Don't know", callback_data=f"dont_know_{word.id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = f"Let's continue learning!\n\n" \
                 f"Word: {word.text}\n" \
                 f"Translation: {word.translation}"
        
        if example:
            message += f"\nExample: {example.sentence}"

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
        )
        
        return LEARNING
    finally:
        db.close()


async def handle_daily_goals(update: Update, context: CallbackContext) -> int:
    """Handle daily goals settings."""
    user = get_user_from_update(update)
    if not user:
        logger.warning(f"User not found for update: {update.effective_user.id}")
        await update.callback_query.edit_message_text(
            "Please /start first to register.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        return MAIN_MENU

    db = SessionLocal()
    try:
        current_word_goal = user.daily_goal_words if hasattr(user, 'daily_goal_words') else 10
        current_time_goal = user.daily_goal_minutes if hasattr(user, 'daily_goal_minutes') else 15

        logger.debug(f"User {user.id} current goals - words: {current_word_goal}, time: {current_time_goal}")

        keyboard = [
            [InlineKeyboardButton("📚 Word Count Goals", callback_data="daily_goals_words")],
            [InlineKeyboardButton("⏱ Time Goals", callback_data="daily_goals_time")],
            [InlineKeyboardButton(BACK_TO_SETTINGS, callback_data="settings")],
            [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
        ]

        await update.callback_query.edit_message_text(
            f"🎯 Daily Learning Goals\n\n"
            f"Current goals:\n"
            f"• Words per day: {current_word_goal}\n"
            f"• Minutes per day: {current_time_goal}\n\n"
            "Choose what to modify:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        logger.info(f"User {user.id} opened daily goals menu")
        return SETTINGS
    finally:
        db.close()


async def handle_daily_goals_words(update: Update, context: CallbackContext) -> int:
    """Handle word count goals settings."""
    user = get_user_from_update(update)
    if not user:
        logger.warning(f"User not found for update: {update.effective_user.id}")
        await update.callback_query.edit_message_text(
            "Please /start first to register.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
            ]),
        )
        return MAIN_MENU

    db = SessionLocal()
    try:
        current_goal = user.daily_goal_words if hasattr(user, 'daily_goal_words') else None
        logger.debug(f"User {user.id} current word goal: {current_goal}")

        keyboard = [
            [InlineKeyboardButton(f"{i} words", callback_data=f"set_goal_words_{i}") 
             for i in [5, 10, 15]],
            [InlineKeyboardButton(f"{i} words", callback_data=f"set_goal_words_{i}") 
             for i in [20, 25, 30]],
            [InlineKeyboardButton(BACK_TO_GOALS, callback_data="daily_goals")],
            [InlineKeyboardButton(BACK_TO_SETTINGS, callback_data="settings")],
            [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
        ]

        await update.callback_query.edit_message_text(
            f"📚 Word Count Goals\n\n"
            f"Current goal: {current_goal} words per day\n\n"
            "Choose your new daily word goal:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        logger.info(f"User {user.id} opened word goals menu")
        return SETTINGS
    finally:
        db.close()


async def handle_daily_goals_time(update: Update, context: CallbackContext) -> int:
    """Handle time goals settings."""
    user = get_user_from_update(update)
    if not user:
        logger.warning(f"User not found for update: {update.effective_user.id}")
        await update.callback_query.edit_message_text(
            "Please /start first to register.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
            ]),
        )
        return MAIN_MENU

    db = SessionLocal()
    try:
        current_goal = user.daily_goal_minutes if hasattr(user, 'daily_goal_minutes') else None
        logger.debug(f"User {user.id} current time goal: {current_goal}")

        keyboard = [
            [InlineKeyboardButton(f"{i} minutes", callback_data=f"set_goal_time_{i}") 
             for i in [5, 10, 15]],
            [InlineKeyboardButton(f"{i} minutes", callback_data=f"set_goal_time_{i}") 
             for i in [20, 30, 45]],
            [InlineKeyboardButton(BACK_TO_GOALS, callback_data="daily_goals")],
            [InlineKeyboardButton(BACK_TO_SETTINGS, callback_data="settings")],
            [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
        ]

        await update.callback_query.edit_message_text(
            f"⏱ Time Goals\n\n"
            f"Current goal: {current_goal} minutes per day\n\n"
            "Choose your new daily time goal:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        logger.info(f"User {user.id} opened time goals menu")
        return SETTINGS
    finally:
        db.close()


async def handle_set_goal(update: Update, context: CallbackContext) -> int:
    """Handle setting a new daily goal."""
    user = get_user_from_update(update)
    if not user:
        logger.warning(f"User not found for update: {update.effective_user.id}")
        await update.callback_query.edit_message_text(
            "Please /start first to register.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")]
            ]),
        )
        return MAIN_MENU

    db = SessionLocal()
    try:
        user_service = UserService(db)
        _, _, goal_type, new_goal = update.callback_query.data.split("_")
        new_goal = int(new_goal)
        
        logger.debug(f"User {user.id} setting new {goal_type} goal to {new_goal}")
        
        if goal_type == "words":
            user_service.update_user_settings(user.id, daily_goal_words=new_goal)
            message = f"✅ Daily word goal updated to {new_goal} words!"
            logger.info(f"User {user.id} updated word goal to {new_goal}")
        else:  # time
            user_service.update_user_settings(user.id, daily_goal_minutes=new_goal)
            message = f"✅ Daily time goal updated to {new_goal} minutes!"
            logger.info(f"User {user.id} updated time goal to {new_goal}")

        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_GOALS, callback_data="daily_goals")],
                [InlineKeyboardButton(BACK_TO_SETTINGS, callback_data="settings")],
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
            ]),
        )
        
        return SETTINGS
    except ValueError as e:
        logger.error(f"Error setting goal for user {user.id}: {str(e)}")
        await update.callback_query.edit_message_text(
            "Error updating goal. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(BACK_TO_GOALS, callback_data="daily_goals")],
                [InlineKeyboardButton(BACK_TO_MENU, callback_data="back_to_menu")],
            ]),
        )
        return SETTINGS
    finally:
        db.close()


def get_user_from_update(update: Update) -> Optional[User]:
    """Get user from database based on update."""
    user = update.effective_user
    if not user:
        return None

    db = SessionLocal()
    try:
        user_service = UserService(db)
        return user_service.get_user_by_telegram_id(user.id)
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