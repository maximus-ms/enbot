#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting EnBot deployment...${NC}"

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

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env file with your configuration before continuing.${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p logs
mkdir -p data/media/pronunciations
mkdir -p data/media/images

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python -m enbot.models.base init_db

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
python -m pytest

# Start the bot
echo -e "${GREEN}Starting EnBot...${NC}"
python -m enbot.app

# Deactivate virtual environment
deactivate 