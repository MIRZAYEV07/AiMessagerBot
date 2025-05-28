from typing import Optional
from sqlalchemy.orm import Session
from app.database import User, get_db
from app.config import settings
from app.utils.logging import setup_logging

logger = setup_logging()


def is_user_allowed(telegram_id: int, db: Session) -> bool:
    """Check if user is allowed to use the bot."""

    # Check if user is in allowed list
    if settings.allowed_users and telegram_id not in settings.allowed_users:
        return False

    # Check database
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        return user.is_allowed

    # If no restrictions are set, allow all users
    if not settings.allowed_users:
        return True

    return False


def is_user_admin(telegram_id: int, db: Session) -> bool:
    """Check if user is an admin."""

    if telegram_id in settings.admin_users:
        return True

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    return user.is_admin if user else False


def get_or_create_user(telegram_id: int, username: Optional[str],
                       first_name: Optional[str], last_name: Optional[str],
                       db: Session) -> User:
    """Get existing user or create new one."""

    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        # Auto-allow if no restrictions
        is_allowed = not settings.allowed_users or telegram_id in settings.allowed_users
        is_admin = telegram_id in settings.admin_users

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_allowed=is_allowed,
            is_admin=is_admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"Created new user: {telegram_id} ({username})")

    return user


def validate_api_key(api_key: str) -> bool:
    """Validate API key for backend access."""
    return api_key == settings.api_key