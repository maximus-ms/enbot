# EnBot API Documentation

## Overview

This document describes the Telegram Bot API interface for EnBot. The bot provides a comprehensive set of commands and interactions for English vocabulary learning.

## Commands

### Basic Commands

#### `/start`
Starts the bot and shows the main menu.

**Response:**
- Main menu with options:
  - Start Learning
  - Add Words
  - Statistics
  - Settings

#### `/help`
Shows help information and available commands.

**Response:**
- List of available commands with descriptions
- Usage examples

### Learning Commands

#### `/learn`
Starts a new learning session.

**Response:**
- First word to learn with:
  - Word text
  - Multiple choice options
  - Pronunciation button
  - Example sentences button
  - Image button (if available)

**User Actions:**
- Select translation
- Listen to pronunciation
- View examples
- View image
- Mark as learned/not learned

#### `/repeat`
Repeats the last learning cycle.

**Response:**
- Words from last cycle
- Quick review format
- Progress tracking

### Word Management

#### `/add`
Adds new words to the dictionary.

**Format:**
```
word1; word2; word3
```

**Response:**
- Confirmation of added words
- Priority selection prompt
- Translation verification

#### `/edit <word>`
Edits an existing word.

**Response:**
- Word details
- Edit options:
  - Translation
  - Priority
  - Examples
  - Notes

### Statistics

#### `/stats`
Shows learning statistics.

**Response:**
- Total words learned
- Daily progress
- Weekly progress
- Monthly progress
- Learning streak
- Time spent learning

#### `/achievements`
Shows user achievements.

**Response:**
- List of achievements
- Progress towards next achievement
- Unlocked badges

### Settings

#### `/settings`
Opens settings menu.

**Options:**
- Language preferences
- Learning goals
- Notification settings
- Daily reminder time
- Minimum daily words
- Minimum daily minutes

#### `/language`
Changes interface language.

**Options:**
- English
- Ukrainian
- Russian
- Polish

## Conversation States

### Main Menu
- Start Learning
- Add Words
- Statistics
- Settings

### Learning
- Word presentation
- Translation selection
- Example viewing
- Image viewing
- Progress tracking

### Add Words
- Word input
- Priority selection
- Translation verification
- Example generation

### Settings
- Language selection
- Goal setting
- Notification configuration
- Time preferences

## Message Types

### Text Messages
- Commands
- Word input
- Settings input

### Inline Keyboard
- Multiple choice options
- Navigation buttons
- Action buttons

### Media Messages
- Pronunciation audio
- Word images
- Example sentences

## Error Handling

### Common Errors
1. Invalid command
   ```
   Error: Unknown command. Use /help to see available commands.
   ```

2. Invalid word format
   ```
   Error: Invalid word format. Please use semicolon-separated words.
   ```

3. Database error
   ```
   Error: Unable to process request. Please try again later.
   ```

4. Rate limiting
   ```
   Error: Too many requests. Please wait a moment.
   ```

### Recovery Actions
- Use /help for command list
- Retry the operation
- Contact support if persistent

## Rate Limits

- Command frequency: 1 command per second
- Word addition: 50 words per minute
- Learning sessions: 10 per hour
- Media requests: 20 per minute

## Best Practices

### For Users
1. Use semicolons to separate multiple words
2. Set realistic daily goals
3. Regular practice sessions
4. Review statistics regularly

### For Developers
1. Handle all error cases
2. Provide clear error messages
3. Implement rate limiting
4. Cache frequently used data

## Examples

### Adding Words
```
User: /add
Bot: Please enter words separated by semicolons.
User: hello; world; python
Bot: Words received. Select priority (1-5):
1. Low
2. Medium
3. High
4. Very High
5. Critical
```

### Learning Session
```
Bot: Let's learn the word "hello"
[Pronunciation button]
[Image button]
[Example button]
Select translation:
1. привіт
2. добрий день
3. вітаю
4. привітання
```

### Statistics
```
Bot: Your Learning Statistics:
📊 Today:
   - Words learned: 15
   - Time spent: 25 minutes
   - Streak: 7 days

📈 Weekly:
   - Total words: 85
   - Average time: 20 minutes/day

🏆 Achievements:
   - 100 Words Master
   - 7 Day Streak
   - Early Bird
``` 