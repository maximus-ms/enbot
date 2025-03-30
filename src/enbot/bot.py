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
from enbot.services.word_service import WordService
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
MENU = "🏠 Menu"
START_LEARNING = "💡 Start Learning"
ADD_NEW_WORDS = "📝 Add New Words"
VIEW_STATISTICS = "📊 View Statistics"

SETTINGS = "⚙️ Settings"
DAILY_GOALS = "🎯 Daily Goals"
NOTIFICATIONS = "🔔 Notifications"

def msg_back_to(text: str) -> str: return f"🔙 {text}"

ERR_MSG_NOT_REGISTERED = "Please /start first to register."
ERR_KB_NOT_REGISTERED = [[InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]]

# Settings options
# CHANGE_LANGUAGE = "Change Language"

KB_BTNS_BACK_TO_MENU_SETTINGS = [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu"),
                                 InlineKeyboardButton(msg_back_to(SETTINGS), callback_data="settings")]

def make_user_id(user_id: int) -> int:
    """Make user id."""
    return user_id# + 1 # TODO: Only for testing


async def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and show main menu."""
    user = update.effective_user
    db = SessionLocal()
    
    try:
        user_service = UserService(db)
        user = user_service.get_or_create_user(
            telegram_id=make_user_id(user.id),
            username=user.first_name,
        )
        
        keyboard = [
            [InlineKeyboardButton(START_LEARNING, callback_data="start_learning")],
            [InlineKeyboardButton(ADD_NEW_WORDS, callback_data="add_words")],
            [InlineKeyboardButton(VIEW_STATISTICS, callback_data="statistics")],
            [InlineKeyboardButton(SETTINGS, callback_data="settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (f"Welcome to EnBot, {user.username}! 👋\n\n"
                    "I'll help you learn English vocabulary effectively.\n"
                    "What would you like to do?")

        # Handle both initial command and callback queries
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
        
        return MAIN_MENU
        
    finally:
        db.close()


async def handle_callback(update: Update, context: CallbackContext) -> int:
    """Handle callback queries from inline keyboard."""
    query = update.callback_query
    await query.answer()

    logger.info("DATA: %s", query.data)

    if query.data == "start_learning":
        return await start_learning(update, context)
    elif query.data.startswith("add_words"):
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
    elif query.data.startswith("add_all_words_from_db"):
        return await handle_add_all_words_from_db(update, context)
    elif query.data.startswith("know_"):
        return await handle_word_response(update, context, True)
    elif query.data.startswith("dont_know_"):
        return await handle_word_response(update, context, False)
    elif query.data == "notifications":
        return await show_notifications(update, context)
    elif query.data.startswith("notifications_set_"):
        return await handle_notifications_set(update, context)
    return MAIN_MENU


async def start_learning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a new learning cycle."""
    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
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
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")],
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
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")],
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
        ("📝 Please enter words (one per line)\n"
        "Or press button to add all words from database\n"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Add all words from database (high priority)", callback_data="add_all_words_from_db_high")],
            [InlineKeyboardButton("Add all words from database (low priority)", callback_data="add_all_words_from_db_low")],
            [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")],
        ]),
    )
    
    return ADD_WORDS


async def handle_add_all_words_from_db(update: Update, context: CallbackContext) -> int:
    """Handle adding all words from database."""
    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return MAIN_MENU

    db = SessionLocal()
    try:
        user_service = UserService(db)
        
        priority = settings.learning.max_priority

        if update.callback_query.data == "add_all_words_from_db_low":
            priority = settings.learning.min_priority

        logger.info("Non user words before")
        words = user_service.get_non_user_words(user.id, 1000)
        logger.info("Non user words: %s", words)

        added_words = user_service.add_words(user.id, words, priority)
        added_words_count = len(added_words)
        if added_words_count == 0: message = "Nothing to add.\n"
        else: message = f"Successfully added {added_words_count} word{'s' if added_words_count > 1 else ''}!\n"
        message += "Would you like to add more words?"

        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu"),
                 InlineKeyboardButton("📝 Add More", callback_data="add_words")],
            ]),
        )
        
        return MAIN_MENU
        
    finally:
        db.close()


async def handle_add_words(update: Update, context: CallbackContext) -> int:
    """Handle adding new words."""
    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return MAIN_MENU

    db = SessionLocal()
    try:
        user_service = UserService(db)

        priority = settings.learning.max_priority

        text = update.message.text
        words = [word.strip() for word in text.split('\n') if word.strip()]
        
        if not words:
            await update.message.reply_text(
                "No valid words provided. Please try again.\n"
                "You can separate words by new lines.\n"
                "Example:\n"
                "hello\n"
                "world\n"
                "python",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]
                ]),
            )
            return ADD_WORDS

        added_words = user_service.add_words(user.id, words, priority)
        added_words_count = len(added_words)
        if added_words_count == 0: message = "Nothing to add.\n"
        else: message = f"Successfully added {added_words_count} word{'s' if added_words_count > 1 else ''}!\n"
        message += "Would you like to add more words?"

        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu"),
                 InlineKeyboardButton("📝 Add More", callback_data="add_words")],
            ]),
        )
        
        return MAIN_MENU
        
    finally:
        db.close()


async def show_statistics(update: Update, context: CallbackContext) -> int:
    """Show user statistics."""
    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return MAIN_MENU

    db = SessionLocal()
    try:
        user_service = UserService(db)
        stats = user_service.get_user_statistics(user.id)
        word_service = WordService(db)
        total_words = word_service.get_word_count()
        total_users = user_service.get_users_count()

        message = ""
        if user.is_admin:
            message += (
                "📊 Global statistics:\n\n"
                f"Total words in database: {total_words}\n"
                f"Total users in database: {total_users}\n\n"
            )

        message += (
            "📊 Your Learning Statistics (Last 30 Days):\n\n"
            f"Total Words Learned: {stats['total_words']}\n"
            f"Total Time Spent: {stats['total_time_minutes']:.1f} minutes\n"
            f"Total Learning Cycles: {stats['total_cycles']}\n"
            f"Average Words per Cycle: {stats['average_words_per_cycle']:.1f}\n"
            f"Average Time per Cycle: {stats['average_time_per_cycle']:.1f} minutes\n"
            f"Total words in your vocabulary: {stats['total_user_words']}\n"
        )
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]
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
        [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")],
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
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
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
                [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]
            ]),
        )
        
        return MAIN_MENU
        
    finally:
        db.close()


async def handle_word_response(update: Update, context: CallbackContext, is_known: bool) -> int:
    """Handle user's response to a word (know/don't know)."""
    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
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
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]
                ]),
            )
            return MAIN_MENU

        # Get the user_word_id for this word
        user_word = (
            db.query(UserWord)
            .filter(
                and_(
                    UserWord.user.id == user.id,
                    UserWord.word_id == word_id,
                )
            )
            .first()
        )
        if not user_word:
            await update.callback_query.edit_message_text(
                "Error: Word not found in your vocabulary.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]
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
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]
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
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")],
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
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return MAIN_MENU

    db = SessionLocal()
    try:
        current_word_goal = user.daily_goal_words if hasattr(user, 'daily_goal_words') else 10
        current_time_goal = user.daily_goal_minutes if hasattr(user, 'daily_goal_minutes') else 10

        logger.debug(f"User {user.id} current goals - words: {current_word_goal}, time: {current_time_goal}")

        keyboard = [
            [InlineKeyboardButton("📚 Word Count Goals", callback_data="daily_goals_words")],
            [InlineKeyboardButton("⏱ Time Goals", callback_data="daily_goals_time")],
            KB_BTNS_BACK_TO_MENU_SETTINGS,
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
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
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
            [InlineKeyboardButton(msg_back_to(DAILY_GOALS), callback_data="daily_goals")],
            KB_BTNS_BACK_TO_MENU_SETTINGS,
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
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
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
            [InlineKeyboardButton(msg_back_to(DAILY_GOALS), callback_data="daily_goals")],
            KB_BTNS_BACK_TO_MENU_SETTINGS,
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
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
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
                [InlineKeyboardButton(msg_back_to(DAILY_GOALS), callback_data="daily_goals")],
                KB_BTNS_BACK_TO_MENU_SETTINGS,
            ]),
        )
        
        return SETTINGS
    except ValueError as e:
        logger.error(f"Error setting goal for user {user.id}: {str(e)}")
        await update.callback_query.edit_message_text(
            "Error updating goal. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(msg_back_to(DAILY_GOALS), callback_data="daily_goals")],
                KB_BTNS_BACK_TO_MENU_SETTINGS,
            ]),
        )
        return SETTINGS
    finally:
        db.close()


async def show_notifications(update: Update, context: CallbackContext) -> int:
    """Show notifications menu."""
    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return MAIN_MENU

    if user.notifications_enabled:
        en_dis_button = InlineKeyboardButton("🔕 Disable notifications", callback_data="notifications_set_off")
        message_status = "Enabled"
    else:
        en_dis_button = InlineKeyboardButton("🔔 Enable notifications", callback_data="notifications_set_on")
        message_status = "Disabled"
    
    keyboard = [
        [en_dis_button],
        [InlineKeyboardButton("🕒 Set time", callback_data="notifications_set_time")],
        KB_BTNS_BACK_TO_MENU_SETTINGS,
    ]
    
    await update.callback_query.edit_message_text(
        f"🔔 Notifications\n\n"
        f"Your notifications are currently set to:\n"
        f"• Time: {user.notification_hour:02d}:00\n"
        f"• Status: {message_status}\n\n"
        "What would you like to do?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    
    return SETTINGS


async def handle_notifications_set(update: Update, context: CallbackContext) -> int:
    """Handle setting notifications."""
    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return MAIN_MENU

    db = SessionLocal()
    try:
        user_service = UserService(db)
        
        keyboard = []

        if update.callback_query.data == "notifications_set_time":
            keyboard.extend([
                [InlineKeyboardButton(f"{i:02d}:00", callback_data=f"notifications_set_time_{i}") for i in range( 7,13)],
                [InlineKeyboardButton(f"{i:02d}:00", callback_data=f"notifications_set_time_{i}") for i in range(13,19)],
                [InlineKeyboardButton(f"{i:02d}:00", callback_data=f"notifications_set_time_{i}") for i in range(19,25)],
                [InlineKeyboardButton(msg_back_to(NOTIFICATIONS), callback_data="notifications")],
            ])
            message = f"🕒 Notifications time\n\n"
            message += f"Your notifications are currently set to:\n"
            message += f"• Time: {user.notification_hour:02d}:00\n"
            message += f"• Status: {'Enabled' if user.notifications_enabled else 'Disabled'}\n\n"
            message += "What time would you like to receive notifications?\nChoose your preferred time:"
        
        elif update.callback_query.data.startswith("notifications_set_time_"):
            hour = int(update.callback_query.data.split("_")[-1])
            user_service.update_user_settings(user.id, notification_hour=hour, notifications_enabled=True)
            message = f"🔔 Notifications will now be sent at {hour:02d}:00!"
            keyboard.append([InlineKeyboardButton(msg_back_to(NOTIFICATIONS), callback_data="notifications")])
        
        elif update.callback_query.data == "notifications_set_off":
            user_service.update_user_settings(user.id, notifications_enabled=False)
            message = "🔕 Notifications disabled!"
            keyboard.append([InlineKeyboardButton(msg_back_to(NOTIFICATIONS), callback_data="notifications")])
        elif update.callback_query.data == "notifications_set_on":
            user_service.update_user_settings(user.id, notifications_enabled=True)
            message = f"🔔 Notifications will now be sent at {user.notification_hour:02d}:00!"
            keyboard.append([InlineKeyboardButton(msg_back_to(NOTIFICATIONS), callback_data="notifications")])

        keyboard.append(KB_BTNS_BACK_TO_MENU_SETTINGS)

        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        return SETTINGS
    except ValueError as e:
        logger.error(f"Error setting notifications for user {user.id}: {str(e)}")
        await update.callback_query.edit_message_text(
            "Error updating notifications. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(msg_back_to(NOTIFICATIONS), callback_data="notifications")],
                KB_BTNS_BACK_TO_MENU_SETTINGS,
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
        return user_service.get_user_by_telegram_id(make_user_id(user.id))
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