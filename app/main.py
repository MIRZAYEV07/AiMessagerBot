from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.ai_agent import AIAgent
from app.telegram_bot import TelegramBot
from app.utils.security import validate_api_key
from app.utils.logging import setup_logging

logger = setup_logging()
security = HTTPBearer()

# Global bot instance
telegram_bot = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global telegram_bot

    # Startup
    logger.info("Starting Telegram AI Bot Backend...")

    telegram_bot = TelegramBot()

    if settings.telegram_webhook_url:
        # Webhook mode
        await telegram_bot.set_webhook(settings.telegram_webhook_url + "/webhook")
        logger.info("Bot configured for webhook mode")
    else:
        # Polling mode
        asyncio.create_task(telegram_bot.run_polling())
        logger.info("Bot started in polling mode")

    yield

    # Shutdown
    logger.info("Shutting down bot...")
    if telegram_bot:
        await telegram_bot.application.stop()


app = FastAPI(
    title="Telegram AI Bot Backend",
    description="Backend API for Telegram AI Bot with conversation management",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models
class MessageRequest(BaseModel):
    user_id: int
    message: str
    session_id: Optional[str] = None


class MessageResponse(BaseModel):
    response: str
    session_id: str
    tokens_used: int
    success: bool
    error: Optional[str] = None


class UserStatsResponse(BaseModel):
    total_messages: int
    total_tokens_used: int
    active_sessions: int


# Dependency for API key validation
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not validate_api_key(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Telegram AI Bot Backend",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "bot_status": "running" if telegram_bot else "not_initialized"
    }


@app.post("/webhook")
async def webhook_handler(update: dict):
    """Handle Telegram webhook updates."""
    if not telegram_bot:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    try:
        from telegram import Update
        telegram_update = Update.de_json(update, telegram_bot.application.bot)
        await telegram_bot.application.process_update(telegram_update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@app.post("/api/message", response_model=MessageResponse)
async def process_message(
        request: MessageRequest,
        db: Session = Depends(get_db),
        api_key: str = Depends(verify_api_key)
):
    """Process a message through the AI agent."""

    try:
        ai_agent = AIAgent(db)
        result = ai_agent.process_message(
            user_id=request.user_id,
            message=request.message,
            session_id=request.session_id
        )

        return MessageResponse(**result)

    except Exception as e:
        logger.error(f"API message processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Message processing failed")


@app.get("/api/stats/{user_id}", response_model=UserStatsResponse)
async def get_user_stats(
        user_id: int,
        db: Session = Depends(get_db),
        api_key: str = Depends(verify_api_key)
):
    """Get user statistics."""

    try:
        ai_agent = AIAgent(db)
        stats = ai_agent.get_user_stats(user_id)
        return UserStatsResponse(**stats)

    except Exception as e:
        logger.error(f"API stats error: {str(e)}")
        raise HTTPException(status_code=500, detail="Stats retrieval failed")


@app.delete("/api/history/{user_id}")
async def clear_user_history(
        user_id: int,
        db: Session = Depends(get_db),
        api_key: str = Depends(verify_api_key)
):
    """Clear user conversation history."""

    try:
        ai_agent = AIAgent(db)
        success = ai_agent.clear_user_history(user_id)

        if success:
            return {"status": "success", "message": "History cleared"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear history")

    except Exception as e:
        logger.error(f"API clear history error: {str(e)}")
        raise HTTPException(status_code=500, detail="Clear history failed")


@app.post("/api/cleanup")
async def cleanup_sessions(
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        api_key: str = Depends(verify_api_key)
):
    """Cleanup expired sessions."""

    def cleanup_task():
        from app.utils.session import SessionManager
        session_manager = SessionManager(db)
        session_manager.cleanup_expired_sessions()

    background_tasks.add_task(cleanup_task)
    return {"status": "cleanup_started"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )