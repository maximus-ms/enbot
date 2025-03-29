# Database Schema Documentation

## Overview

EnBot uses SQLite as its database system, with SQLAlchemy as the ORM. This document describes the database schema, relationships, and key operations.

## Tables

### Users

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP,
    settings JSON,
    is_admin BOOLEAN DEFAULT FALSE
);
```

**Relationships:**
- One-to-many with UserWords
- One-to-many with LearningCycles
- One-to-many with UserActivities

### Words

```sql
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    translation TEXT NOT NULL,
    transcription TEXT,
    pronunciation_file TEXT,
    image_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    examples JSON,
    synonyms JSON,
    antonyms JSON
);
```

**Relationships:**
- One-to-many with UserWords
- One-to-many with CycleWords

### UserWords

```sql
CREATE TABLE user_words (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    priority INTEGER DEFAULT 3,
    is_learned BOOLEAN DEFAULT FALSE,
    last_reviewed TIMESTAMP,
    next_review TIMESTAMP,
    review_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (word_id) REFERENCES words(id),
    UNIQUE(user_id, word_id)
);
```

**Relationships:**
- Many-to-one with Users
- Many-to-one with Words

### LearningCycles

```sql
CREATE TABLE learning_cycles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    words_per_cycle INTEGER DEFAULT 10,
    new_words_ratio REAL DEFAULT 0.3,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Relationships:**
- Many-to-one with Users
- One-to-many with CycleWords

### CycleWords

```sql
CREATE TABLE cycle_words (
    id INTEGER PRIMARY KEY,
    cycle_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    is_learned BOOLEAN DEFAULT FALSE,
    learned_at TIMESTAMP,
    FOREIGN KEY (cycle_id) REFERENCES learning_cycles(id),
    FOREIGN KEY (word_id) REFERENCES words(id)
);
```

**Relationships:**
- Many-to-one with LearningCycles
- Many-to-one with Words

### UserActivities

```sql
CREATE TABLE user_activities (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Relationships:**
- Many-to-one with Users

## Indexes

```sql
-- Users
CREATE INDEX idx_users_telegram_id ON users(telegram_id);

-- Words
CREATE INDEX idx_words_text ON words(text);
CREATE INDEX idx_words_translation ON words(translation);

-- UserWords
CREATE INDEX idx_user_words_user_id ON user_words(user_id);
CREATE INDEX idx_user_words_word_id ON user_words(word_id);
CREATE INDEX idx_user_words_next_review ON user_words(next_review);

-- LearningCycles
CREATE INDEX idx_learning_cycles_user_id ON learning_cycles(user_id);
CREATE INDEX idx_learning_cycles_is_active ON learning_cycles(is_active);

-- UserActivities
CREATE INDEX idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX idx_user_activities_created_at ON user_activities(created_at);
```

## Common Queries

### Get User's Words for Learning

```sql
SELECT w.*, uw.priority, uw.next_review
FROM words w
JOIN user_words uw ON w.id = uw.word_id
WHERE uw.user_id = ? AND uw.is_learned = FALSE
ORDER BY uw.priority DESC, uw.next_review ASC
LIMIT ?;
```

### Get Active Learning Cycle

```sql
SELECT c.*, COUNT(cw.id) as word_count
FROM learning_cycles c
LEFT JOIN cycle_words cw ON c.id = cw.cycle_id
WHERE c.user_id = ? AND c.is_active = TRUE
GROUP BY c.id;
```

### Get User Statistics

```sql
SELECT 
    COUNT(DISTINCT uw.word_id) as total_words,
    SUM(CASE WHEN uw.is_learned = TRUE THEN 1 ELSE 0 END) as learned_words,
    COUNT(DISTINCT c.id) as total_cycles,
    MAX(c.completed_at) as last_completed_cycle
FROM users u
LEFT JOIN user_words uw ON u.id = uw.user_id
LEFT JOIN learning_cycles c ON u.id = c.user_id
WHERE u.id = ?;
```

## Data Integrity

### Constraints
- Unique telegram_id for users
- Unique (user_id, word_id) combination for user_words
- Valid priority range (1-5)
- Valid new_words_ratio range (0-1)

### Triggers
- Update updated_at timestamp on word updates
- Update last_active timestamp on user activity
- Update review_count on word review

## Backup and Recovery

### Backup Strategy
1. Regular SQLite database file backup
2. Media files backup
3. Configuration backup

### Recovery Process
1. Restore database file
2. Restore media files
3. Verify data integrity
4. Update indexes

## Performance Considerations

### Optimization Techniques
1. Indexed columns for frequent queries
2. JSON storage for flexible data
3. Efficient joins for related data
4. Connection pooling

### Monitoring
1. Query performance tracking
2. Index usage monitoring
3. Database size monitoring
4. Connection pool status

## Maintenance

### Regular Tasks
1. Vacuum database
2. Update statistics
3. Check index usage
4. Verify data integrity

### Cleanup Tasks
1. Remove unused media files
2. Archive old activities
3. Optimize JSON storage
4. Update review schedules 