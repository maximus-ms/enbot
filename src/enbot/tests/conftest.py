"""Test configuration."""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Set test environment before any imports
os.environ["ENV"] = "test"

# Load test environment variables
test_env_path = Path(__file__).parent.parent.parent / ".env.test"
load_dotenv(test_env_path)

# Import after environment setup
from enbot.config import ensure_directories


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Ensure test directories exist
    ensure_directories()
    
    yield
    
    # Cleanup after test (if needed)
    pass 