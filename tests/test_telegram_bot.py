import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User, Chat
from app.telegram_bot import TelegramBot
from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_telegram.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_update():
    """Create a mock Telegram update."""
    user = User(id=123, first_name="Test", username="testuser", is_bot=False)
    chat = Chat(id=123, type="private")
    message = Message(message_id=1, date=None, chat=chat, from_user=user, text="Hello")

    update = Mock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    update.message.reply_text = AsyncMock()

    return update


@pytest.fixture
def mock_context():
    """Create a mock context."""
    context = Mock()
    context.bot.send_chat_action = AsyncMock()
    return context


class TestTelegramBot:

    @pytest.mark.asyncio
    async def test_start_command(self, mock_update, mock_context):
        """Test /start command."""

        with patch('app.telegram_bot.get_db') as mock_get_db, \
                patch('app.telegram_bot.is_user_allowed', return_value=True), \
                patch('app.telegram_bot.get_or_create_user'):
            mock_get_db.return_value.__enter__.return_value = Mock()

            bot = TelegramBot()
            await bot.start_command(mock_update, mock_context)

            # Verify welcome message was sent
            mock_update.message.reply_text.assert_called_once()
            args = mock_update.message.reply_text.call_args[0]
            assert "Welcome to AI Assistant Bot" in args[0]

    @pytest.mark.asyncio
    async def test_handle_message_success(self, mock_update, mock_context):
        """Test successful message handling."""

        with patch('app.telegram_bot.get_db') as mock_get_db, \
                patch('app.telegram_bot.is_user_allowed', return_value=True), \
                patch('app.telegram_bot.AIAgent') as mock_ai_agent:
            # Mock database
            mock_get_db.return_value.__enter__.return_value = Mock()

            # Mock AI agent response
            mock_ai_agent.return_value.process_message.return_value = {
                "success": True,
                "response": "AI response",
                "tokens_used": 25
            }

            bot = TelegramBot()
            await bot.handle_message(mock_update, mock_context)

            # Verify response was sent
            mock_update.message.reply_text.assert_called_once()
            args = mock_update.message.reply_text.call_args[0]
            assert args[0] == "AI response"

    @pytest.mark.asyncio
    async def test_handle_message_access_denied(self, mock_update, mock_context):
        """Test message handling with access denied."""

        with patch('app.telegram_bot.get_db') as mock_get_db, \
                patch('app.telegram_bot.is_user_allowed', return_value=False):
            mock_get_db.return_value.__enter__.return_value = Mock()

            bot = TelegramBot()
            await bot.handle_message(mock_update, mock_context)

            # Verify access denied message was sent
            mock_update.message.reply_text.assert_called_once()
            args = mock_update.message.reply_text.call_args[0]
            assert "don't have access" in args[0]