"""Main Telegram bot module."""
import logging
import random
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
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from enbot.config import settings
from enbot.models.base import SessionLocal
from enbot.models.models import User, UserWord, CycleWord
from enbot.services.learning_service import LearningService
from enbot.services.user_service import UserService
from enbot.services.word_service import WordService
from sqlalchemy import and_

# Get logger for this module
logger = logging.getLogger(__name__)

# Conversation states
MAIN_MENU, ADDING_WORDS = range(2)

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


async def log_received(update: Update, context_type: str) -> None:
    """Log message."""
    logger.info(f"Received @{context_type:8} from user {update.effective_user.username} ({update.effective_user.id})")


async def handle_start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and show main menu."""
    user = update.effective_user
    db = SessionLocal()
    
    await log_received(update, "start")
    
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

    await log_received(update, "callback")

    if query.data == "start_learning":
        return await start_learning(update, context)
    elif query.data.startswith("learning_response_"):
        return await handle_learning_response(update, context)
    elif query.data.startswith("add_words"):
        return await add_words(update, context)
    elif query.data == "statistics":
        return await show_statistics(update, context)
    elif query.data == "settings":
        return await show_settings(update, context)
    elif query.data == "back_to_menu":
        return await handle_start(update, context)
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
    elif query.data == "notifications":
        return await show_notifications(update, context)
    elif query.data.startswith("notifications_set_"):
        return await handle_notifications_set(update, context)
    
    return MAIN_MENU


async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle messages."""
    user = get_user_from_update(update)
    if not user: 
        await update.message.reply_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return

    await log_received(update, "message")

    await update.message.reply_text("Please start with /start")

    return MAIN_MENU


async def start_learning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a new learning cycle."""
    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return MAIN_MENU

    db = SessionLocal()
    try:
        user_service = UserService(db)

        learning_service = LearningService(db)
        words, cycle = learning_service.get_words_for_cycle_or_create(user.id)
        logger.info(f"User {user.id} has {len(words)} words for learning")
        if not words:
            await update.callback_query.edit_message_text(
                "No words available for learning. Add some words first!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu"),
                    InlineKeyboardButton("📝 Add Words", callback_data="add_words")],
                ]),
            )
            return MAIN_MENU

        word = random.choice(words).word
        example = word.examples[0] if word.examples else None

        # Show the first word
        keyboard = [[
            InlineKeyboardButton("🤷‍♂️ I don't know", callback_data=f"learning_response_dontknow_{word.id}"),
            InlineKeyboardButton("❌ Don't learn", callback_data=f"learning_response_dontlearn_{word.id}"),    
            InlineKeyboardButton("✅ I know this", callback_data=f"learning_response_know_{word.id}")],
            [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (f"Let's learn some words!\n\n"
                   f"Word: {word.text}\n"
                   f"Translation: {word.translation}")
        
        if example: message += f"\nExample: {example.sentence}"

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
        )
        
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
    
    return ADDING_WORDS


async def handle_add_all_words_from_db(update: Update, context: CallbackContext) -> None:
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

        words = user_service.get_non_user_words(user.id, 1000)

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
        
    finally:
        db.close()


async def handle_add_words(update: Update, context: CallbackContext) -> int:
    """Handle adding new words."""
    user = get_user_from_update(update)

    if not user: 
        await update.message.reply_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
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
            return ADDING_WORDS

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
        
    finally:
        db.close()

    return ADDING_WORDS


async def show_statistics(update: Update, context: CallbackContext) -> None:
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
        
    finally:
        db.close()

    return MAIN_MENU


async def show_settings(update: Update, context: CallbackContext) -> None:
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

    return MAIN_MENU


async def handle_language_selection(update: Update, context: CallbackContext) -> None:
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
        
    finally:
        db.close()

    return MAIN_MENU
async def handle_learning_response(update: Update, context: CallbackContext) -> None:
    """Handle user's response to a word (know/don't know)."""

    user = get_user_from_update(update)
    if not user: 
        await update.callback_query.edit_message_text(ERR_MSG_NOT_REGISTERED, reply_markup=ERR_KB_NOT_REGISTERED)
        return MAIN_MENU

    db = SessionLocal()
    try:
        learning_service = LearningService(db)
        #learning_response_dontknow_123
        _, _, action, word_id = update.callback_query.data.split("_")
        polarity = not "dont" in action
        action = action.replace("dont", "").strip()
         
        # Get the current cycle
        words, cycle = learning_service.get_words_for_cycle(user.id)
        if not words:
            await update.callback_query.edit_message_text(
                "No active learning cycle found. Please start learning again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(START_LEARNING, callback_data="start_learning")],
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]
                ]),
            )
            return

        word = None
        word_ix = None
        for ix, w in enumerate(words):
            if w.id == int(word_id):
                word = w
                word_ix = ix
                break

        if not word:
            await update.callback_query.edit_message_text(
                "Error: Word not found in current learning cycle.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(START_LEARNING, callback_data="start_learning")],
                    [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")]
                ]),
            )
            return

        # Mark the word as learned if user knows it
        if polarity and action == "know":
            learning_service.mark_word_as_learned(cycle.id, word.id, 0.0)  # Time spent is 0 for now
            words.pop(word_ix)
        elif not polarity and action == "learn":
            learning_service.remove_word_from_cycle(cycle.id, word.id)
            user_service = UserService(db)
            user_service.delete_user_word(user.id, word.id)
            words.pop(word_ix)
            
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
            return

        # Show the next word
        word = random.choice(words).word
        example = word.examples[0] if word.examples else None

        keyboard = [
            [InlineKeyboardButton("🤷‍♂️ I don't know", callback_data=f"learning_response_dontknow_{word.id}"),
            InlineKeyboardButton("❌ Don't learn", callback_data=f"learning_response_dontlearn_{word.id}"),    
            InlineKeyboardButton("✅ I know this", callback_data=f"learning_response_know_{word.id}")],
            [InlineKeyboardButton(msg_back_to(MENU), callback_data="back_to_menu")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (f"Let's continue learning!\n\n"
                   f"Word: {word.text}\n"
                   f"Translation: {word.translation}")
        
        if example: message += f"\nExample: {example.sentence}"

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
        )
        
    finally:
        db.close()

    return MAIN_MENU
async def handle_daily_goals(update: Update, context: CallbackContext) -> None:
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
    finally:
        db.close()

    return MAIN_MENU


async def handle_daily_goals_words(update: Update, context: CallbackContext) -> None:
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
    finally:
        db.close()

    return MAIN_MENU
async def handle_daily_goals_time(update: Update, context: CallbackContext) -> None:
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
    finally:
        db.close()

    return MAIN_MENU
async def handle_set_goal(update: Update, context: CallbackContext) -> None:
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
        
    except ValueError as e:
        logger.error(f"Error setting goal for user {user.id}: {str(e)}")
        await update.callback_query.edit_message_text(
            "Error updating goal. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(msg_back_to(DAILY_GOALS), callback_data="daily_goals")],
                KB_BTNS_BACK_TO_MENU_SETTINGS,
            ]),
        )
    finally:
        db.close()

    return MAIN_MENU
async def show_notifications(update: Update, context: CallbackContext) -> None:
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
    
    return MAIN_MENU


async def handle_notifications_set(update: Update, context: CallbackContext) -> None:
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
        
    except ValueError as e:
        logger.error(f"Error setting notifications for user {user.id}: {str(e)}")
        await update.callback_query.edit_message_text(
            "Error updating notifications. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(msg_back_to(NOTIFICATIONS), callback_data="notifications")],
                KB_BTNS_BACK_TO_MENU_SETTINGS,
            ]),
        )
    finally:
        db.close()

    return MAIN_MENU


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
    application = Application.builder().token(settings.bot.token).build()

    application.add_handler(CommandHandler("start", handle_start))

    # Add callback query handler (buttons)
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", handle_start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
            ],
            ADDING_WORDS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_words),
            ],
        },
        fallbacks=[CommandHandler("start", handle_start)],
    )

    # Add conversation handler
    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    main() 