from groq import Groq
import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from ..core.config import settings
from ..core.database import get_db, Conversation, UserSession
from .models import ChatRequest, ChatResponse

client = Groq(
    api_key=settings.GROQ_API_KEY,
)

class AIAgent:
    def __init__(self):
        self.model = settings.GROQ_AI_MODEL
        self.max_tokens = settings.MAX_TOKENS
        self.conversation_memory = {}  # In-memory cache for active sessions

    async def process_message(self, user_id: int, message: str, session_id: str = None) -> ChatResponse:
        """Process user message and return AI response"""
        start_time = time.time()

        try:
            # Get or create session context
            context = await self._get_session_context(user_id, session_id)

            # Add user message to context
            context.append({"role": "user", "content": message})

            # Generate AI response
            response = await self._generate_response(context)

            # Add AI response to context
            context.append({"role": "assistant", "content": response})

            # Update session context
            await self._update_session_context(user_id, session_id, context)

            # Log conversation
            processing_time = int((time.time() - start_time) * 1000)
            await self._log_conversation(user_id, message, response, processing_time)

            return ChatResponse(
                response=response,
                session_id=session_id,
                processing_time=processing_time,
                success=True
            )

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            return ChatResponse(
                response="I'm sorry, I encountered an error processing your request. Please try again.",
                session_id=session_id,
                error=error_msg,
                success=False
            )

    async def _generate_response(self, context: List[Dict]) -> str:
        """Generate AI response using OpenAI API"""
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=context,
                max_tokens=self.max_tokens,
                temperature=0.7,
                timeout=30
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def _get_session_context(self, user_id: int, session_id: str) -> List[Dict]:
        """Get conversation context for user session"""
        if session_id in self.conversation_memory:
            return self.conversation_memory[session_id].copy()

        # Load from database
        db = next(get_db())
        try:
            session = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.session_id == session_id,
                UserSession.is_active == True
            ).first()

            if session and session.context:
                context = json.loads(session.context)
                self.conversation_memory[session_id] = context
                return context.copy()
        except Exception as e:
            print(f"Error loading session context: {e}")
        finally:
            db.close()

        # Return default system context
        return [
            {
                "role": "system",
                "content": "You are a helpful AI assistant integrated with Telegram. Provide clear, concise, and helpful responses."
            }
        ]

    async def _update_session_context(self, user_id: int, session_id: str, context: List[Dict]):
        """Update session context in memory and database"""
        # Keep only last 20 messages to manage memory
        if len(context) > 20:
            context = context[:1] + context[-19:]  # Keep system message + last 19

        # Update memory cache
        self.conversation_memory[session_id] = context

        # Update database
        db = next(get_db())
        try:
            session = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.session_id == session_id
            ).first()

            if session:
                session.context = json.dumps(context)
                session.updated_at = datetime.utcnow()
            else:
                session = UserSession(
                    user_id=user_id,
                    session_id=session_id,
                    context=json.dumps(context)
                )
                db.add(session)

            db.commit()
        except Exception as e:
            print(f"Error updating session context: {e}")
            db.rollback()
        finally:
            db.close()

    async def _log_conversation(self, user_id: int, message: str, response: str, processing_time: int):
        """Log conversation to database"""
        db = next(get_db())
        try:
            conversation = Conversation(
                user_id=user_id,
                message=message,
                response=response,
                processing_time=processing_time
            )
            db.add(conversation)
            db.commit()
        except Exception as e:
            print(f"Error logging conversation: {e}")
            db.rollback()
        finally:
            db.close()

    async def clear_session(self, user_id: int, session_id: str):
        """Clear user session context"""
        if session_id in self.conversation_memory:
            del self.conversation_memory[session_id]

        db = next(get_db())
        try:
            db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.session_id == session_id
            ).update({"is_active": False})
            db.commit()
        except Exception as e:
            print(f"Error clearing session: {e}")
            db.rollback()
        finally:
            db.close()


# Global AI agent instance
ai_agent = AIAgent()