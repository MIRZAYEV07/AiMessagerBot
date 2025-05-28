import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database import UserSession, get_db
from app.config import settings


class SessionManager:
    """Manage user sessions and conversation context."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: int) -> str:
        """Create a new session for user."""
        session_id = str(uuid.uuid4())

        # Deactivate old sessions
        self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).update({"is_active": False})

        # Create new session
        session = UserSession(
            user_id=user_id,
            session_id=session_id,
            context_data="{}",
            is_active=True
        )

        self.db.add(session)
        self.db.commit()

        return session_id

    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get active session."""
        return self.db.query(UserSession).filter(
            UserSession.session_id == session_id,
            UserSession.is_active == True
        ).first()

    def get_user_active_session(self, user_id: int) -> Optional[UserSession]:
        """Get user's active session."""
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).first()

    def update_session_context(self, session_id: str, context: Dict[str, Any]):
        """Update session context."""
        session = self.get_session(session_id)
        if session:
            session.context_data = json.dumps(context)
            session.last_updated = datetime.utcnow()
            self.db.commit()

    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get session context."""
        session = self.get_session(session_id)
        if session and session.context_data:
            try:
                return json.loads(session.context_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        expiry_time = datetime.utcnow() - timedelta(seconds=settings.session_timeout)

        self.db.query(UserSession).filter(
            UserSession.last_updated < expiry_time
        ).update({"is_active": False})

        self.db.commit()