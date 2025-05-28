import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.ai_agent import AIAgent
from app.utils.security import is_user_allowed, is_user_admin, get_or_create_user
from app.utils.logging import setup_logging

logger = setup_logging()


class TelegramBot:
    """Telegram Bot Handler."""

    def __init__(self):
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup command and message handlers."""

        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))

        # Message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def start_command(self, update: Update, context):
        """Handle /start command."""

        user = update.effective_user
        db = next(get_db())

        try:
            # Create or get user
            db_user = get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                db=db
            )

            if not is_user_allowed(user.id, db):
                await update.message.reply_text(
                    "❌ Sorry, you don't have access to this bot. Please contact an administrator."
                )
                return

            welcome_text = f"""
🤖 **Welcome to AI Assistant Bot!**

Hello {user.first_name}! I'm your AI assistant powered by advanced language models.

**What I can help you with:**
• Answer questions on any topic
• Provide summaries and explanations  
• Help with task planning and automation
• General conversation and brainstorming

**Commands:**
/help - Show available commands
/stats - View your usage statistics
/clear - Clear conversation history

Just send me a message and I'll respond intelligently!
            """

            await update.message.reply_text(welcome_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in start command: {str(e)}")
            await update.message.reply_text("An error occurred. Please try again.")
        finally:
            db.close()

    async def help_command(self, update: Update, context):
        """Handle /help command."""

        help_text = """
🆘 **Help & Commands**

**Available Commands:**
• `/start` - Initialize the bot
• `/help` - Show this help message
• `/stats` - View your usage statistics
• `/clear` - Clear your conversation history
• `/admin` - Admin panel (admins only)

**How to use:**
Just send me any message and I'll respond with helpful information. I can:

📝 **Answer Questions** - Ask me anything!
📊 **Provide Summaries** - Send me text to summarize
🎯 **Task Planning** - Help you plan and organize tasks
💬 **General Chat** - Have natural conversations

**Tips:**
• Be specific in your questions for better responses
• Use markdown formatting in your messages
• Your conversation history is maintained across sessions
        """

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def stats_command(self, update: Update, context):
        """Handle /stats command."""

        user = update.effective_user
        db = next(get_db())

        try:
            if not is_user_allowed(user.id, db):
                await update.message.reply_text("❌ Access denied.")
                return

            ai_agent = AIAgent(db)
            stats = ai_agent.get_user_stats(user.id)

            stats_text = f"""
📊 **Your Usage Statistics**

• **Total Messages:** {stats['total_messages']}
• **Tokens Used:** {stats['total_tokens_used']:,}
• **Active Sessions:** {stats['active_sessions']}

Keep chatting to explore more capabilities! 🚀
            """

            await update.message.reply_text(stats_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in stats command: {str(e)}")
            await update.message.reply_text("Error retrieving statistics.")
        finally:
            db.close()

    async def clear_command(self, update: Update, context):
        """Handle /clear command."""

        user = update.effective_user
        db = next(get_db())

        try:
            if not is_user_allowed(user.id, db):
                await update.message.reply_text("❌ Access denied.")
                return

            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, Clear History", callback_data="clear_confirm"),
                    InlineKeyboardButton("❌ Cancel", callback_data="clear_cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "⚠️ **Clear Conversation History**\n\n"
                "This will clear your conversation history and end your current session. "
                "Are you sure you want to continue?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in clear command: {str(e)}")
            await update.message.reply_text("Error processing clear request.")
        finally:
            db.close()

    async def admin_command(self, update: Update, context):
        """Handle /admin command."""

        user = update.effective_user
        db = next(get_db())

        try:
            if not is_user_admin(user.id, db):
                await update.message.reply_text("❌ Admin access required.")
                return

            # Get system stats
            total_users = db.query(User).count()
            total_conversations = db.query(Conversation).count()
            active_sessions = db.query(UserSession).filter(UserSession.is_active == True).count()

            admin_text = f"""
🔧 **Admin Panel**

**System Statistics:**
• Total Users: {total_users}
• Total Conversations: {total_conversations}
• Active Sessions: {active_sessions}

**Admin Commands:**
Use the buttons below to manage the system.
            """

            keyboard = [
                [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
                [InlineKeyboardButton("🧹 Cleanup Sessions", callback_data="admin_cleanup")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                admin_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in admin command: {str(e)}")
            await update.message.reply_text("Error accessing admin panel.")
        finally:
            db.close()

    async def handle_message(self, update: Update, context):
        """Handle regular text messages."""

        user = update.effective_user
        message_text = update.message.text
        db = next(get_db())

        try:
            # Check user access
            if not is_user_allowed(user.id, db):
                await update.message.reply_text(
                    "❌ Sorry, you don't have access to this bot. Use /start to begin."
                )
                return

            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

            # Process with AI
            ai_agent = AIAgent(db)
            result = ai_agent.process_message(user.id, message_text)

            if result["success"]:
                # Send response
                await update.message.reply_text(
                    result["response"],
                    parse_mode='Markdown'
                )

                logger.info(f"Response sent to user {user.id}, tokens: {result['tokens_used']}")
            else:
                await update.message.reply_text(
                    "❌ Sorry, I encountered an error processing your message. Please try again."
                )

        except Exception as e:
            logger.error(f"Error handling message from user {user.id}: {str(e)}")
            await update.message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )
        finally:
            db.close()

    async def handle_callback(self, update: Update, context):
        """Handle callback queries from inline keyboards."""

        query = update.callback_query
        user = update.effective_user
        data = query.data
        db = next(get_db())

        try:
            await query.answer()

            if data == "clear_confirm":
                if is_user_allowed(user.id, db):
                    ai_agent = AIAgent(db)
                    if ai_agent.clear_user_history(user.id):
                        await query.edit_message_text(
                            "✅ **History Cleared**\n\n"
                            "Your conversation history has been cleared successfully. "
                            "You can start a fresh conversation now!",
                            parse_mode='Markdown'
                        )
                    else:
                        await query.edit_message_text("❌ Error clearing history.")
                else:
                    await query.edit_message_text("❌ Access denied.")

            elif data == "clear_cancel":
                await query.edit_message_text(
                    "✅ **Cancelled**\n\nYour conversation history remains intact."
                )

            elif data.startswith("admin_"):
                if not is_user_admin(user.id, db):
                    await query.edit_message_text("❌ Admin access required.")
                    return

                await self._handle_admin_callback(query, data, db)

        except Exception as e:
            logger.error(f"Error handling callback {data} from user {user.id}: {str(e)}")
            await query.edit_message_text("❌ Error processing request.")
        finally:
            db.close()

    async def _handle_admin_callback(self, query, data: str, db: Session):
        """Handle admin callback queries."""

        if data == "admin_cleanup":
            from app.utils.session import SessionManager
            session_manager = SessionManager(db)
            session_manager.cleanup_expired_sessions()

            await query.edit_message_text(
                "✅ **Cleanup Complete**\n\n"
                "Expired sessions have been cleaned up successfully."
            )

        elif data == "admin_stats":
            # Get detailed statistics
            total_tokens = db.query(Conversation).with_entities(Conversation.tokens_used).all()
            total_tokens_used = sum([t[0] for t in total_tokens if t[0]])

            recent_users = db.query(User).filter(
                User.last_active >= datetime.utcnow() - timedelta(days=7)
            ).count()

            stats_text = f"""
📊 **Detailed System Statistics**

**Usage:**
• Total Tokens Used: {total_tokens_used:,}
• Active Users (7 days): {recent_users}
• Average Tokens per Message: {total_tokens_used // max(len(total_tokens), 1):,}

**Database:**
• Total Users: {db.query(User).count()}
• Total Conversations: {db.query(Conversation).count()}
• Active Sessions: {db.query(UserSession).filter(UserSession.is_active == True).count()}
            """

            await query.edit_message_text(stats_text, parse_mode='Markdown')

    async def run_polling(self):
        """Run bot with polling."""
        logger.info("Starting Telegram bot with polling...")
        await self.application.run_polling(drop_pending_updates=True)

    async def set_webhook(self, webhook_url: str):
        """Set webhook for the bot."""
        logger.info(f"Setting webhook to: {webhook_url}")
        await self.application.bot.set_webhook(url=webhook_url)