#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up EnBot development environment...${NC}"

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install development dependencies
echo -e "${YELLOW}Installing development dependencies...${NC}"
pip install -r requirements-dev.txt

# Install pre-commit hooks
echo -e "${YELLOW}Installing pre-commit hooks...${NC}"
pre-commit install

# Create necessary directories
# echo -e "${YELLOW}Creating necessary directories...${NC}"
# mkdir -p logs
# mkdir -p data/media/pronunciations
# mkdir -p data/media/images

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env file with your configuration before continuing.${NC}"
    exit 1
fi

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python -m enbot.models.base init_db

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
python -m pytest

# Run code style checks
echo -e "${YELLOW}Running code style checks...${NC}"
flake8 src/enbot
black --check src/enbot

echo -e "${GREEN}Development environment setup complete!${NC}"
echo -e "${YELLOW}To start development:${NC}"
echo -e "1. Activate virtual environment: ${GREEN}source venv/bin/activate${NC}"
echo -e "2. Start the bot: ${GREEN}python -m enbot.app${NC}"
echo -e "3. Run tests: ${GREEN}python -m pytest${NC}"
echo -e "4. Check code style: ${GREEN}flake8 src/enbot${NC}"
echo -e "5. Format code: ${GREEN}black src/enbot${NC}" 