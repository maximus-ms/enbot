# EnBot Architecture Overview

## System Components

### 1. Core Components

#### 1.1 Telegram Bot Interface (`bot.py`)
- Handles user interactions via Telegram
- Manages conversation states and flows
- Routes commands to appropriate services
- Implements user interface elements

#### 1.2 Application Core (`app.py`)
- Main application entry point
- Initializes and coordinates all services
- Manages application lifecycle
- Handles graceful shutdown

#### 1.3 Configuration (`config.py`)
- Manages application settings
- Loads environment variables
- Validates configuration
- Provides type-safe settings access

### 2. Services Layer

#### 2.1 User Service (`services/user_service.py`)
- Manages user data and preferences
- Handles user registration and authentication
- Tracks user progress and statistics
- Manages user settings

#### 2.2 Learning Service (`services/learning_service.py`)
- Implements learning algorithms
- Manages learning cycles
- Handles word selection and prioritization
- Tracks learning progress

#### 2.3 Content Service (`services/content_service.py`)
- Generates learning content
- Manages word translations
- Handles media content (images, audio)
- Creates example sentences

#### 2.4 Notification Service (`services/notification_service.py`)
- Manages user notifications
- Handles reminders and alerts
- Sends achievement notifications
- Manages notification preferences

#### 2.5 Scheduler Service (`services/scheduler_service.py`)
- Manages scheduled tasks
- Handles periodic notifications
- Coordinates background jobs
- Manages task priorities

### 3. Data Layer

#### 3.1 Database Models (`models/`)
- `user.py`: User data and preferences
- `word.py`: Word definitions and content
- `cycle.py`: Learning cycle management
- `activity.py`: User activity tracking

#### 3.2 Database Management
- SQLAlchemy ORM for database operations
- SQLite for data storage
- Migration management
- Connection pooling

### 4. Monitoring and Logging

#### 4.1 Monitoring (`monitoring.py`)
- Prometheus metrics collection
- Performance monitoring
- Error tracking
- Usage statistics

#### 4.2 Logging (`logging_config.py`)
- Structured logging
- Log rotation
- Log levels management
- Error tracking

## Data Flow

1. User Interaction Flow:
   ```
   User -> Telegram Bot -> Command Handler -> Service Layer -> Database
   ```

2. Learning Cycle Flow:
   ```
   Scheduler -> Learning Service -> Word Selection -> Content Generation -> User
   ```

3. Notification Flow:
   ```
   Scheduler -> Notification Service -> User
   ```

## Key Design Decisions

### 1. Modular Architecture
- Services are independent and loosely coupled
- Each service has a single responsibility
- Easy to extend and maintain
- Simple to test

### 2. State Management
- Conversation states managed by Telegram Bot
- Learning states tracked in database
- User preferences stored persistently
- Activity tracking for analytics

### 3. Data Storage
- SQLite for simplicity and portability
- File-based storage for media content
- Efficient indexing for quick access
- Regular backups recommended

### 4. Performance Considerations
- Asynchronous operations where possible
- Connection pooling for database
- Caching for frequently accessed data
- Efficient media file handling

### 5. Security
- Environment-based configuration
- Secure storage of sensitive data
- Input validation and sanitization
- Rate limiting for API calls

## Deployment Architecture

### 1. Development Environment
- Local SQLite database
- File-based media storage
- Development logging
- Debug mode enabled

### 2. Production Environment
- Containerized deployment
- Persistent volume storage
- Production logging
- Monitoring enabled

## Future Considerations

### 1. Scalability
- Database sharding
- Load balancing
- Caching layer
- Distributed storage

### 2. Features
- Additional learning methods
- More media content types
- Advanced analytics
- Social features

### 3. Integration
- External API integrations
- Third-party services
- Analytics platforms
- Backup services

## Development Guidelines

### 1. Code Organization
- Follow modular design
- Maintain clear separation of concerns
- Use dependency injection
- Keep services independent

### 2. Testing Strategy
- Unit tests for services
- Integration tests for flows
- End-to-end tests for features
- Performance testing

### 3. Documentation
- Keep documentation up to date
- Document API changes
- Maintain architecture diagrams
- Update deployment guides 