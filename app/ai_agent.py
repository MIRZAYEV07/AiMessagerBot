import openai
import json
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Conversation
from app.utils.logging import setup_logging
from app.utils.session import SessionManager

logger = setup_logging()


class AIAgent:
    """AI Agent for processing user queries."""

    def __init__(self, db: Session):
        self.db = db
        self.session_manager = SessionManager(db)
        openai.api_key = settings.openai_api_key

        self.system_prompt = """You are a helpful AI assistant integrated with a Telegram bot. 
        You can help users with various tasks including:
        - Answering questions
        - Providing summaries
        - Task automation and planning
        - General conversation

        Keep responses concise but informative. Use markdown formatting when appropriate.
        If you need clarification, ask follow-up questions."""

    def process_message(self, user_id: int, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process user message and generate response."""

        try:
            # Get or create session
            if not session_id:
                session = self.session_manager.get_user_active_session(user_id)
                if not session:
                    session_id = self.session_manager.create_session(user_id)
                else:
                    session_id = session.session_id

            # Get conversation history
            conversation_history = self._get_conversation_history(user_id, session_id)

            # Prepare messages for AI
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})

            # Get AI response
            response = openai.ChatCompletion.create(
                model=settings.ai_model,
                messages=messages,
                max_tokens=settings.max_tokens,
                temperature=0.7
            )

            ai_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            # Save conversation
            self._save_conversation(user_id, session_id, message, ai_response, tokens_used)

            # Update session context
            context = self.session_manager.get_session_context(session_id)
            context["last_message"] = message
            context["last_response"] = ai_response
            context["total_tokens"] = context.get("total_tokens", 0) + tokens_used
            self.session_manager.update_session_context(session_id, context)

            logger.info(f"AI response generated for user {user_id}, tokens: {tokens_used}")

            return {
                "response": ai_response,
                "session_id": session_id,
                "tokens_used": tokens_used,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {str(e)}")
            return {
                "response": "Sorry, I encountered an error processing your request. Please try again.",
                "session_id": session_id,
                "tokens_used": 0,
                "success": False,
                "error": str(e)
            }

    def _get_conversation_history(self, user_id: int, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history."""

        conversations = self.db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.session_id == session_id
        ).order_by(Conversation.timestamp.desc()).limit(limit * 2).all()

        # Convert to OpenAI format
        messages = []
        for conv in reversed(conversations):
            role = "user" if conv.message_type == "user" else "assistant"
            messages.append({"role": role, "content": conv.content})

        return messages

    def _save_conversation(self, user_id: int, session_id: str, user_message: str,
                           ai_response: str, tokens_used: int):
        """Save conversation to database."""

        # Save user message
        user_conv = Conversation(
            user_id=user_id,
            session_id=session_id,
            message_type="user",
            content=user_message,
            tokens_used=0
        )

        # Save AI response
        ai_conv = Conversation(
            user_id=user_id,
            session_id=session_id,
            message_type="assistant",
            content=ai_response,
            tokens_used=tokens_used
        )

        self.db.add_all([user_conv, ai_conv])
        self.db.commit()

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics."""

        total_conversations = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).count()

        total_tokens = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).with_entities(Conversation.tokens_used).all()

        total_tokens_used = sum([t[0] for t in total_tokens if t[0]])

        return {
            "total_messages": total_conversations,
            "total_tokens_used": total_tokens_used,
            "active_sessions": self.db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).count()
        }

    def clear_user_history(self, user_id: int) -> bool:
        """Clear user's conversation history."""

        try:
            # Deactivate sessions
            self.db.query(UserSession).filter(
                UserSession.user_id == user_id
            ).update({"is_active": False})

            # Note: We keep conversations for analytics but mark sessions as inactive
            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error clearing history for user {user_id}: {str(e)}")
            return False