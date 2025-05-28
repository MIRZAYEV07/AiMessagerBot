import time
from functools import wraps
from collections import defaultdict, deque
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from ..core.config import settings

# Rate limiting storage
user_message_times = defaultdict(deque)


def rate_limiter(func):
    """Rate limiting decorator"""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        current_time = datetime.now()

        # Clean old messages outside window
        window_start = current_time - timedelta(seconds=settings.RATE_LIMIT_WINDOW)
        user_times = user_message_times[user_id]

        while user_times and user_times[0] < window_start:
            user_times.popleft()

        # Check rate limit
        if len(user_times) >= settings.RATE_LIMIT_MESSAGES:
            await update.message.reply_text(
                f"⚠️ **Rate limit exceeded!**\n\n"
                f"Please wait a moment before sending another message.\n"
                f"Limit: {settings.RATE_LIMIT_MESSAGES} messages per {settings.RATE_LIMIT_WINDOW} seconds."
            )
            return

        # Add current message time
        user_times.append(current_time)

        return await func(update, context, *args, **kwargs)

    return wrapper


def access_control(func):
    """Access control decorator"""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id

        # Check whitelist if configured
        if settings.WHITELISTED_USERS and user_id not in settings.WHITELISTED_USERS:
            await update.message.reply_text(
                "🚫 **Access Denied**\n\n"
                "You don't have permission to use this bot.\n"
                "Please contact the administrator for access."
            )
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


def admin_only(func):
    """Admin-only decorator"""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id

        if user_id not in settings.ADMIN_USER_IDS:
            await update.message.reply_text(
                "🚫 **Admin Access Required**\n\n"
                "This command requires administrator privileges."
            )
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


