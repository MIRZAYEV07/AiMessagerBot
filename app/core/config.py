import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")

    # AI Settings
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    AI_MODEL: str = Field("gpt-3.5-turbo", env="AI_MODEL")
    MAX_TOKENS: int = Field(1000, env="MAX_TOKENS")
    GROQ_API_KEY: str = Field(..., env="GROQ_API_KEY")
    GROQ_AI_MODEL: str = Field("llama-3.3-70b-versatile", env="GROQ_AI_MODEL")

    # Backend API Settings
    API_HOST: str = Field("0.0.0.0", env="API_HOST")
    API_PORT: int = Field(8000, env="API_PORT")
    API_SECRET_KEY: str = Field(..., env="API_SECRET_KEY")

    # Database Settings
    DATABASE_URL: str = Field("sqlite:///./telegram_bot.db", env="DATABASE_URL")

    # Access Control
    WHITELISTED_USERS: List[int] = Field(default_factory=list, env="WHITELISTED_USERS")
    ADMIN_USER_IDS: List[int] = Field(default_factory=list, env="ADMIN_USER_IDS")

    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field("bot.log", env="LOG_FILE")

    # Rate Limiting
    RATE_LIMIT_MESSAGES: int = Field(10, env="RATE_LIMIT_MESSAGES")
    RATE_LIMIT_WINDOW: int = Field(60, env="RATE_LIMIT_WINDOW")  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()