# EnBot - English Learning Telegram Bot

EnBot is a Telegram bot designed to help users learn English vocabulary through interactive lessons, spaced repetition, and personalized learning paths.

## Features

- 📚 Interactive vocabulary learning
- 🔄 Spaced repetition system
- 🎯 Personalized learning paths
- 📊 Progress tracking and statistics
- 🏆 Achievement system
- 🔔 Smart notifications and reminders
- 🎨 Visual learning aids (images)
- 🔊 Audio pronunciations
- 🌐 Multi-language support

## Prerequisites

- Python 3.12 or higher
- Telegram Bot Token (get it from [@BotFather](https://t.me/botfather))
- SQLite (included in Python)

## Installation

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/enbot.git
   cd enbot
   ```

2. Build and run the Docker container:
   ```bash
   docker-compose up -d
   ```

3. Check the logs:
   ```bash
   docker-compose logs -f
   ```

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/enbot.git
   cd enbot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the deployment script:
   ```bash
   ./scripts/deploy.sh
   ```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your settings:
   - `TELEGRAM_BOT_TOKEN`: Your bot token from BotFather
   - `TELEGRAM_ADMIN_IDS`: Comma-separated list of admin user IDs
   - Other settings as needed

## Usage

1. Start the bot:
   ```bash
   python -m enbot.app
   ```

2. Open Telegram and start a chat with your bot

3. Available commands:
   - `/start` - Start the bot and show main menu
   - `/help` - Show help message
   - `/add` - Add new words to your dictionary
   - `/learn` - Start a learning session
   - `/stats` - View your learning statistics
   - `/settings` - Configure your preferences

## Development

### Running Tests

```bash
python -m pytest
```

### Code Style

This project follows PEP 8 guidelines. To check code style:

```bash
flake8 src/enbot
```

### Adding New Features

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run tests:
   ```bash
   python -m pytest
   ```

4. Submit a pull request

## Project Structure

```
enbot/
├── src/
│   └── enbot/
│       ├── models/         # Database models
│       ├── services/       # Business logic
│       ├── tests/         # Test files
│       ├── app.py         # Main application
│       ├── bot.py         # Telegram bot handlers
│       ├── config.py      # Configuration
│       └── logging_config.py  # Logging setup
├── scripts/               # Utility scripts
├── data/                 # Data files
│   └── media/           # Media files
├── logs/                # Log files
├── tests/              # Integration tests
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
├── docker-compose.yml # Docker Compose configuration
└── README.md         # This file
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Faker](https://faker.readthedocs.io/)