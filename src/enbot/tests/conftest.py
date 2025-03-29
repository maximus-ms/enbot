"""Test configuration."""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load test environment variables
test_env_path = Path(__file__).parent.parent.parent / ".env.test"
load_dotenv(test_env_path) 