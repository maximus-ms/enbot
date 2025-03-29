# EnBot Technical Specification

## Project Overview
EnBot is a Telegram-based English learning assistant that helps users learn vocabulary through interactive exercises, spaced repetition, and comprehensive word information. The bot supports multiple language pairs and provides personalized learning experiences.

## Core Features

### 1. Word Management
- **Input Format**: Flexible delimiter support for word/phrase input
- **Word Storage**: 
  - Support for both single words and phrases
  - Per-user word priority system (10 levels)
  - Priority management:
    - New words can be assigned highest priority
    - Priority downgrade cascade (current_priority - 1) for existing words
    - Priority changes only affect words within the same priority set
    - Cooldown system:
      - 1-month inactivity reduces priority by 1
      - Only affects words with priority > 5
    - Special priority for repetition words:
      - Words due for repetition get priority level 11 (highest_priority + 1)
      - Priority 11 words are temporary and only used for scheduling
  - Duplicate detection with priority updates
  - Separate storage for pronunciations and images
  - File-based storage for media with database references

### 2. Learning System
- **Learning Models**:
  - Multiple choice translation selection
  - Translation guessing with similar options
  - Typing-based word input
  - Extensible model architecture for future additions
- **Model Sets**:
  - Configurable combination of learning models
  - Default set includes all three basic models
  - Words considered learned only after completing the selected model set
- **Learning Cycle**:
  - Default cycle size: 10 words (user-configurable)
  - One cycle per day
  - Cycle Management:
    - Multiple cycles per day allowed after completion
    - Unfinished cycles continue to next day
    - Configurable day start time (default: 3 AM)
  - Word Selection Algorithm:
    - Maximum 70% of words from repetition history (priority 11)
    - Remaining 30% from current priority sets
    - Words selected from highest priority set first
    - Fallback to lower priority sets if needed
    - Random selection within each word set:
      - Random selection from words due for repetition
      - Random selection from current priority sets
      - Ensures even distribution of word exposure
  - Words removed from cycle after marking as learned
  - No new words added during active cycle
  - End-of-cycle review:
    - Repeat all learned words
    - Simple test for verification
    - Mistakes don't affect learned status

### 3. Spaced Repetition
- **Default Intervals**: 1, 3, 5, 10 days, and 1 month
- **Customization**:
  - Configurable number of repetition periods
  - Adjustable period lengths in days
  - Per-user settings

### 4. Daily Learning Goals
- **Configurable Targets**:
  - Minimum daily learning time (minutes)
  - Minimum daily word count
  - Notification system for unmet goals
  - Empty dictionary notifications

### 5. Multi-language Support
- **Language Pairs**:
  - Support for multiple language pairs per user
  - Separate progress tracking per language pair
  - Independent dictionaries per language pair
  - Shared Telegram chat interface

### 6. Content Generation
- **Word Information**:
  - Translation (mandatory)
  - Transcription (for English)
  - Pronunciation (audio files)
  - Example sentences (3-5 per word):
    - Short, meaningful sentences
    - User feedback mechanism for quality
    - Ability to regenerate poor examples
  - Related images:
    - Size: 320x240 (configurable)
    - Optimized for storage and loading
- **Content Sources**:
  - AI-based API integration
  - Rate-limited content generation
  - Local storage of generated content
  - Progressive content population

### 7. Administrative Features
- **Admin Panel**:
  - Multiple admin support
  - Master admin privileges
  - Secure admin addition mechanism
  - User statistics viewing
  - Manual database table deletion capability
  - No automatic data deletion
  - Database size statistics
  - Mode switching:
    - Admin mode for administrative tasks
    - User mode for learning activities
    - Seamless switching between modes
- **Communication**:
  - Concise message format
  - Minimal chat overload
  - Clear, short notifications

### 8. Database Management
- **Access**:
  - Manual GUI access
  - Separate databases per language pair
  - Persistent storage
  - File system integration for media
- **Storage Structure**:
  - Single root directory for all databases
  - Per-user database files
  - No size limits per user
  - No automatic optimization
  - Manual backup through directory copying
- **Logging System**:
  - Priority changes logging (per user)
  - Learning cycle completion logging
  - Word addition logging
  - Word learning status changes
  - All changes logged with timestamps
  - Per-user log history

### 9. Statistics
- **Core Metrics**:
  - Learning time tracking
  - Word count tracking
  - Per-user progress
  - Per-language pair progress
- **Future Expansion**:
  - Extensible metrics system
  - Additional statistics as needed

## Technical Architecture

### 1. Modular Design
- **Frontend**:
  - Telegram Bot interface
  - User interaction handling
  - Command processing
- **Backend**:
  - Core business logic
  - Learning algorithms
  - Content management
  - Database operations

### 2. Data Storage
- **Database Structure**:
  - User profiles
  - Word dictionaries
  - Learning progress
  - Statistics
  - Change logs
  - Priority history
- **File System**:
  - Pronunciation audio files
  - Word images
  - Organized by word/phrase identifiers
  - Manual backup support through directory copying

### 3. Deployment
- **Containerization**:
  - Docker-based deployment
  - 24/7 availability
  - Scalable architecture
- **Version Control**:
  - Git-based repository
  - Regular commits
  - Branch management

## Security Considerations
- Secure admin management
- Protected user data
- Rate limiting for API calls
- Access control for database operations
- Backup system security

## Future Extensibility
- Additional learning models
- New language pair support
- Enhanced content generation
- Advanced analytics
- Custom learning algorithms
- Potential gamification features

## Implementation Notes
- Python-based development
- Modular code structure
- Clear separation of concerns
- Comprehensive error handling
- Detailed logging system
- Regular backup mechanisms

## Monitoring and Maintenance
- System health monitoring
- Performance metrics
- Usage statistics
- Error tracking
- Regular maintenance procedures
- Database backup monitoring 