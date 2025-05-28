import os
from typing import List, Optional
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Telegram Bot Configuration
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_webhook_url: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL")

    # AI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "gpt-3.5-turbo")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "1000"))

    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./telegram_bot.db")

    # Security Configuration
    allowed_users: List[int] = []
    admin_users: List[int] = []
    api_key: str = os.getenv("API_KEY", "your-secret-api-key")

    # Server Configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Session Configuration
    session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour

    class Config:
        env_file = ".env"


settings = Settings()

# Parse allowed users from environment
if os.getenv("ALLOWED_USERS"):
    settings.allowed_users = [int(x.strip()) for x in os.getenv("ALLOWED_USERS").split(",")]

if os.getenv("ADMIN_USERS"):
    settings.admin_users = [int(x.strip()) for x in os.getenv("ADMIN_USERS").split(",")]