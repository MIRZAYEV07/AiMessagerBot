from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time
from datetime import datetime
from typing import List

from ..core.config import settings
from ..core.database import get_db, User, Conversation, UserSession
from .models import ChatRequest, ChatResponse, UserInfo, SessionClearRequest
from .ai_agent import ai_agent

app = FastAPI(title="Telegram AI Bot Backend", version="1.0.0")
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return credentials.credentials


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
        request: ChatRequest,
        background_tasks: BackgroundTasks,
        token: str = Depends(verify_token)
):
    """Process chat message through AI agent"""
    try:
        # Generate session ID if not provided
        if not request.session_id:
            request.session_id = f"session_{request.user_id}_{int(time.time())}"

        # Process message
        response = await ai_agent.process_message(
            user_id=request.user_id,
            message=request.message,
            session_id=request.session_id
        )
        print(">>>>ASJKASJS",response)

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/users", response_model=dict)
async def create_or_update_user(
        user_info: UserInfo,
        db=Depends(get_db),
        token: str = Depends(verify_token)
):
    """Create or update user information"""
    try:
        user = db.query(User).filter(User.telegram_user_id == user_info.telegram_user_id).first()

        if user:
            # Update existing user
            user.username = user_info.username
            user.first_name = user_info.first_name
            user.last_name = user_info.last_name
            user.last_seen = datetime.utcnow()
        else:
            # Create new user
            user = User(
                telegram_user_id=user_info.telegram_user_id,
                username=user_info.username,
                first_name=user_info.first_name,
                last_name=user_info.last_name
            )
            db.add(user)

        db.commit()
        return {"status": "success", "message": "User updated successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/sessions/clear")
async def clear_session(
        request: SessionClearRequest,
        token: str = Depends(verify_token)
):
    """Clear user session context"""
    try:
        await ai_agent.clear_session(request.user_id, request.session_id)
        return {"status": "success", "message": "Session cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    print(">>>>>>>.,",datetime.utcnow())
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.get("/stats")
async def get_stats(token: str = Depends(verify_token), db=Depends(get_db)):
    """Get bot statistics"""
    try:
        total_users = db.query(User).count()
        total_conversations = db.query(Conversation).count()
        active_sessions = db.query(UserSession).filter(UserSession.is_active == True).count()

        return {
            "total_users": total_users,
            "total_conversations": total_conversations,
            "active_sessions": active_sessions,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


