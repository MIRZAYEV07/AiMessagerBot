import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from app.bot.handlers import BotHandlers
from app.core.config import settings


@pytest.fixture
def bot_handlers():
    return BotHandlers()


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.effective_user.first_name = "Test"
    update.effective_user.username = "testuser"
    update.message = MagicMock(spec=Message)
    update.message.text = "Hello, bot!"
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 123456789
    return update


@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_start_command(bot_handlers, mock_update, mock_context):
    """Test /start command handler"""
    with patch.object(bot_handlers, '_update_user_info', new=AsyncMock()):
        mock_update.message.reply_text = AsyncMock()

        await bot_handlers.start_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Welcome to AI Assistant Bot" in call_args[0][0]


@pytest.mark.asyncio
async def test_help_command(bot_handlers, mock_update, mock_context):
    """Test /help command handler"""
    mock_update.message.reply_text = AsyncMock()

    await bot_handlers.help_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "AI Assistant Bot Help" in call_args[0][0]


@pytest.mark.asyncio
async def test_handle_message(bot_handlers, mock_update, mock_context):
    """Test message handling"""
    mock_response = {
        "success": True,
        "response": "Hello! How can I help you today?"
    }

    with patch.object(bot_handlers, '_send_to_ai_backend', new=AsyncMock(return_value=mock_response)):
        mock_update.message.reply_text = AsyncMock()
        mock_context.bot.send_chat_action = AsyncMock()

        await bot_handlers.handle_message(mock_update, mock_context)

        mock_context.bot.send_chat_action.assert_called_once()
        mock_update.message.reply_text.assert_called_once_with(mock_response["response"])


@pytest.mark.asyncio
async def test_clear_command(bot_handlers, mock_update, mock_context):
    """Test /clear command handler"""
    user_id = mock_update.effective_user.id
    bot_handlers.user_sessions[user_id] = "test_session_123"

    with patch.object(bot_handlers, '_clear_session', new=AsyncMock()):
        mock_update.message.reply_text = AsyncMock()

        await bot_handlers.clear_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Conversation cleared" in call_args[0][0]

        # Check that new session ID was generated
        assert bot_handlers.user_sessions[user_id] != "test_session_123"