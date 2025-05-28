import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import uvicorn
from threading import Thread
import traceback

from .core.config import settings
from .bot.handlers import bot_handlers
from .backend.api import app as fastapi_app

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Also enable telegram library logging
logging.getLogger("telegram").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.INFO)


class TelegramAIBot:
    def __init__(self):
        self.telegram_app = None
        self.fastapi_thread = None

    def start_fastapi_server(self):
        """Start FastAPI server in a separate thread"""
        try:
            logger.info(f"Starting FastAPI server on {settings.API_HOST}:{settings.API_PORT}")
            uvicorn.run(
                fastapi_app,
                host=settings.API_HOST,
                port=settings.API_PORT,
                log_level=settings.LOG_LEVEL.lower()
            )
        except Exception as e:
            logger.error(f"Failed to start FastAPI server: {e}")
            logger.error(traceback.format_exc())

    async def start_telegram_bot(self):
        """Start Telegram bot"""
        try:
            logger.info("Initializing Telegram bot...")

            # Validate token
            if not settings.TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

            if not settings.TELEGRAM_BOT_TOKEN.startswith(('bot', 'BOT')):
                logger.warning("Bot token doesn't start with 'bot' - this might be incorrect")

            logger.info(f"Using bot token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")

            # Create application with more explicit configuration
            self.telegram_app = (
                Application.builder()
                .token(settings.TELEGRAM_BOT_TOKEN)
                .concurrent_updates(True)  # Enable concurrent updates
                .build()
            )

            # Test bot token by getting bot info
            bot_info = await self.telegram_app.bot.get_me()
            logger.info(f"Bot info: @{bot_info.username} ({bot_info.first_name})")

            # Add handlers with logging
            logger.info("Adding command handlers...")
            self.telegram_app.add_handler(CommandHandler("start", self.wrapped_start_command))
            self.telegram_app.add_handler(CommandHandler("help", self.wrapped_help_command))
            self.telegram_app.add_handler(CommandHandler("clear", self.wrapped_clear_command))
            self.telegram_app.add_handler(CommandHandler("stats", self.wrapped_stats_command))

            # Add message handler for all text messages
            logger.info("Adding message handler...")
            self.telegram_app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.wrapped_handle_message)
            )

            # Add callback query handler
            logger.info("Adding callback query handler...")
            self.telegram_app.add_handler(CallbackQueryHandler(self.wrapped_button_callback))

            # Error handler
            self.telegram_app.add_error_handler(self.error_handler)

            logger.info("Starting Telegram bot polling...")

            # Initialize and start
            await self.telegram_app.initialize()
            await self.telegram_app.start()

            # Start polling with error handling
            await self.telegram_app.updater.start_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True,  # Drop pending updates on startup
                bootstrap_retries=3,
                read_timeout=10,
                write_timeout=10,
                connect_timeout=10,
                pool_timeout=5
            )

            logger.info("Telegram bot started successfully! Waiting for messages...")

            # Keep the bot running indefinitely
            # This prevents the async function from ending and cancelling the polling
            try:
                # Wait indefinitely until interrupted
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("Bot polling cancelled")
                raise

        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            logger.error(traceback.format_exc())
            raise

    # Wrapped handlers with logging and error handling
    async def wrapped_start_command(self, update, context):
        """Wrapped start command with logging"""
        try:
            logger.info(f"Start command from user {update.effective_user.id}")
            await bot_handlers.start_command(update, context)
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            logger.error(traceback.format_exc())
            await self.send_error_message(update, "Error processing start command")

    async def wrapped_help_command(self, update, context):
        """Wrapped help command with logging"""
        try:
            logger.info(f"Help command from user {update.effective_user.id}")
            await bot_handlers.help_command(update, context)
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await self.send_error_message(update, "Error processing help command")

    async def wrapped_clear_command(self, update, context):
        """Wrapped clear command with logging"""
        try:
            logger.info(f"Clear command from user {update.effective_user.id}")
            await bot_handlers.clear_command(update, context)
        except Exception as e:
            logger.error(f"Error in clear command: {e}")
            await self.send_error_message(update, "Error processing clear command")

    async def wrapped_stats_command(self, update, context):
        """Wrapped stats command with logging"""
        try:
            logger.info(f"Stats command from user {update.effective_user.id}")
            await bot_handlers.stats_command(update, context)
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await self.send_error_message(update, "Error processing stats command")

    async def wrapped_handle_message(self, update, context):
        """Wrapped message handler with logging"""
        try:
            user_id = update.effective_user.id
            message = update.message.text[:50] + "..." if len(update.message.text) > 50 else update.message.text
            logger.info(f"Message from user {user_id}: {message}")

            await bot_handlers.handle_message(update, context)
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            logger.error(traceback.format_exc())
            await self.send_error_message(update, "Error processing your message")

    async def wrapped_button_callback(self, update, context):
        """Wrapped button callback with logging"""
        try:
            logger.info(f"Button callback from user {update.effective_user.id}: {update.callback_query.data}")
            await bot_handlers.button_callback(update, context)
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
            await self.send_error_message(update, "Error processing button click")

    async def send_error_message(self, update, message):
        """Send error message to user"""
        try:
            if update.message:
                await update.message.reply_text(f"❌ {message}. Please try again.")
            elif update.callback_query:
                await update.callback_query.message.reply_text(f"❌ {message}. Please try again.")
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    async def error_handler(self, update, context):
        """Enhanced error handler"""
        logger.error(f"Update {update} caused error {context.error}")
        logger.error(traceback.format_exc())

        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Please try again or contact support."
                )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")

    async def shutdown(self):
        """Shutdown bot gracefully"""
        logger.info("Shutting down bot...")

        try:
            if bot_handlers.session:
                await bot_handlers.close_session()

            if self.telegram_app:
                await self.telegram_app.updater.stop()
                await self.telegram_app.stop()
                await self.telegram_app.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

        logger.info("Bot shutdown complete")

    def run(self):
        """Run both FastAPI and Telegram bot"""
        try:
            # Start FastAPI server in background thread
            logger.info("Starting FastAPI server in background...")
            self.fastapi_thread = Thread(target=self.start_fastapi_server, daemon=True)
            self.fastapi_thread.start()

            # Give FastAPI time to start
            import time
            time.sleep(2)

            logger.info("FastAPI server started, now starting Telegram bot...")

            # Start Telegram bot in main thread
            asyncio.run(self.start_telegram_bot())

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}")
            logger.error(traceback.format_exc())
        finally:
            try:
                asyncio.run(self.shutdown())
            except Exception as e:
                logger.error(f"Error during final shutdown: {e}")


def main():
    """Main entry point with validation"""
    # Validate critical settings
    if not hasattr(settings, 'TELEGRAM_BOT_TOKEN') or not settings.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in settings!")
        return

    if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
        print("WARNING: OPENAI_API_KEY is not set in settings!")

    print(f"Starting bot with token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"OpenAI API Key set: {'Yes' if settings.OPENAI_API_KEY else 'No'}")

    bot = TelegramAIBot()
    bot.run()


if __name__ == "__main__":
    main()