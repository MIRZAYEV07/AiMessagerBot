from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatRequest(BaseModel):
    user_id: int
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
    processing_time: Optional[int] = None
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

class UserInfo(BaseModel):
    telegram_user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class SessionClearRequest(BaseModel):
    user_id: int
    session_id: str