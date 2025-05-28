import logging
import sys
from datetime import datetime
from typing import Optional
from app.config import settings


class ColoredFormatter(logging.Formatter):
    """Colored log formatter."""

    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging():
    """Setup application logging."""

    # Create logger
    logger = logging.getLogger("telegram_ai_bot")
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler("app.log")
    file_handler.setLevel(logging.INFO)

    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )

    # Add formatters to handlers
    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def log_conversation(user_id: int, message: str, response: str, tokens_used: Optional[int] = None):
    """Log conversation for analytics."""
    logger = logging.getLogger("telegram_ai_bot")
    logger.info(f"Conversation - User: {user_id}, Tokens: {tokens_used}, "
                f"Message: {message[:100]}..., Response: {response[:100]}...")