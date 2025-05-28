import pytest
import asyncio
from unittest.mock import patch
import os

# Set test environment variables
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
os.environ["OPENAI_API_KEY"] = "test_openai_key"
os.environ["API_SECRET_KEY"] = "test_secret_key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment"""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.TELEGRAM_BOT_TOKEN = "test_token"
        mock_settings.OPENAI_API_KEY = "test_openai_key"
        mock_settings.API_SECRET_KEY = "test_secret_key"
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        mock_settings.WHITELISTED_USERS = []
        mock_settings.ADMIN_USER_IDS = [123456789]
        mock_settings.RATE_LIMIT_MESSAGES = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        yield