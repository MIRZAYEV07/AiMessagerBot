import asyncio
import logging

import aiohttp
import uuid
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict

from ..core.config import settings
from ..core.database import get_db, User, Conversation
from .middleware import rate_limiter, access_control

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.LOG_LEVEL),
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self):
        self.api_base_url = f"http://localhost:{settings.API_PORT}"
        self.session = None
        self.user_sessions: Dict[int, str] = {}  # user_id -> session_id

    async def init_session(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    # @access_control
    # @rate_limiter
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        print("ishladiiIIIIIIIIII")
        user = update.effective_user
        logger.debug("Start command triggered by user: %s", user)

        # Create/update user in backend
        await self._update_user_info(user)

        welcome_message = f"""
🤖 **Welcome to AI Assistant Bot!**

Hello {user.first_name}! I'm your AI assistant powered by advanced language models.

**Available Commands:**
• Send any message - I'll respond intelligently
• /help - Show this help message
• /clear - Clear conversation history
• /stats - Show your usage statistics

Just type your question or message, and I'll help you with:
✅ Answering questions
✅ Explaining concepts
✅ Creative writing
✅ Problem solving
✅ And much more!

Let's get started! 🚀
        """

        keyboard = [
            [InlineKeyboardButton("📊 My Stats", callback_data="user_stats")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    # @access_control
    # @rate_limiter
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
🤖 **AI Assistant Bot Help**

**Commands:**
• `/start` - Welcome message and setup
• `/help` - Show this help message
• `/clear` - Clear conversation history
• `/stats` - Your usage statistics

**Features:**
• 💬 **Smart Conversations** - I remember context within our chat
• 🧠 **Intelligent Responses** - Powered by advanced AI
• 📚 **Knowledge Base** - I can help with various topics
• 🔒 **Privacy** - Your conversations are secure

**Tips:**
• Be specific in your questions for better responses
• I can help with creative writing, explanations, analysis, and more
• Use /clear to start a fresh conversation
• Check /stats to see your usage

**Need more help?** Just ask me anything!
        """

        await update.message.reply_text(help_message, parse_mode='Markdown')

    # @access_control
    # @rate_limiter
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        user_id = update.effective_user.id

        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]

            # Clear session via API
            await self._clear_session(user_id, session_id)

            # Generate new session ID
            self.user_sessions[user_id] = f"session_{user_id}_{int(datetime.now().timestamp())}"

        await update.message.reply_text(
            "🧹 **Conversation cleared!**\n\nYour chat history has been reset. Let's start fresh!",
            parse_mode='Markdown'
        )

    # @access_control
    # @rate_limiter
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = update.effective_user.id

        # Get user stats from database
        stats = await self._get_user_stats(user_id)

        stats_message = f"""
📊 **Your Statistics**

• **Messages sent:** {stats.get('total_messages', 0)}
• **Responses received:** {stats.get('total_responses', 0)}
• **Active since:** {stats.get('member_since', 'Unknown')}
• **Last activity:** {stats.get('last_activity', 'Now')}

Keep chatting to learn more! 🚀
        """

        await update.message.reply_text(stats_message, parse_mode='Markdown')

    # @access_control
    # @rate_limiter
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_id = update.effective_user.id
        message_text = update.message.text

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Get or create session ID
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = f"session_{user_id}_{int(datetime.now().timestamp())}"

        session_id = self.user_sessions[user_id]

        try:
            # Send message to AI backend
            response = await self._send_to_ai_backend(user_id, message_text, session_id)

            if response and response.get('success'):
                ai_response = response['response']

                # Split long messages
                if len(ai_response) > 4096:
                    # Split message into chunks
                    chunks = [ai_response[i:i + 4096] for i in range(0, len(ai_response), 4096)]
                    for chunk in chunks:
                        await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(ai_response)
            else:
                error_msg = response.get('error', 'Unknown error occurred')
                await update.message.reply_text(
                    f"❌ Sorry, I encountered an error: {error_msg}\n\nPlease try again or contact support."
                )

        except Exception as e:
            await update.message.reply_text(
                "❌ I'm temporarily unavailable. Please try again in a moment."
            )
            print(f"Error handling message: {e}")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == "help":
            await self.help_command(update, context)
        elif query.data == "user_stats":
            await self.stats_command(update, context)

    async def _send_to_ai_backend(self, user_id: int, message: str, session_id: str) -> dict:
        """Send message to AI backend API"""
        await self.init_session()

        try:
            headers = {
                "Authorization": f"Bearer {settings.API_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "user_id": user_id,
                "message": message,
                "session_id": session_id
            }

            async with self.session.post(
                    f"{self.api_base_url}/chat",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"API error: {error_text}"}

        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    async def _clear_session(self, user_id: int, session_id: str):
        """Clear user session via API"""
        await self.init_session()

        try:
            headers = {
                "Authorization": f"Bearer {settings.API_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "user_id": user_id,
                "session_id": session_id
            }

            async with self.session.post(
                    f"{self.api_base_url}/sessions/clear",
                    json=payload,
                    headers=headers
            ) as response:
                pass  # Just fire and forget

        except Exception as e:
            print(f"Error clearing session: {e}")

    async def _update_user_info(self, user):
        """Update user information via API"""
        await self.init_session()

        try:
            headers = {
                "Authorization": f"Bearer {settings.API_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "telegram_user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            }

            async with self.session.post(
                    f"{self.api_base_url}/users",
                    json=payload,
                    headers=headers
            ) as response:
                pass  # Just fire and forget

        except Exception as e:
            print(f"Error updating user info: {e}")

    async def _get_user_stats(self, user_id: int) -> dict:
        """Get user statistics from database"""
        db = next(get_db())
        try:
            user = db.query(User).filter(User.telegram_user_id == user_id).first()
            if user:
                return {
                    "total_messages": db.query(Conversation).filter(Conversation.user_id == user_id).count(),
                    "total_responses": db.query(Conversation).filter(Conversation.user_id == user_id).count(),
                    "member_since": user.created_at.strftime("%Y-%m-%d"),
                    "last_activity": user.last_seen.strftime("%Y-%m-%d %H:%M")
                }
            return {}
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}
        finally:
            db.close()


# Global handlers instance
bot_handlers = BotHandlers()