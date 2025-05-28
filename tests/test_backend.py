import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.backend.api import app
from app.backend.ai_agent import AIAgent
from app.backend.models import ChatRequest, ChatResponse
from app.core.config import settings

client = TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {settings.API_SECRET_KEY}"}


@pytest.fixture
def ai_agent():
    return AIAgent()


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_chat_endpoint_unauthorized():
    """Test chat endpoint without authorization"""
    response = client.post("/chat", json={
        "user_id": 123456789,
        "message": "Hello"
    })
    assert response.status_code == 403


def test_chat_endpoint_authorized(auth_headers):
    """Test chat endpoint with authorization"""
    with patch('app.backend.ai_agent.ai_agent.process_message') as mock_process:
        mock_process.return_value = ChatResponse(
            response="Hello! How can I help you?",
            session_id="test_session",
            success=True
        )

        response = client.post("/chat", json={
            "user_id": 123456789,
            "message": "Hello"
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Hello! How can I help you?" in data["response"]


@pytest.mark.asyncio
async def test_ai_agent_process_message(ai_agent):
    """Test AI agent message processing"""
    with patch.object(ai_agent, '_generate_response', new=AsyncMock(return_value="Test response")):
        with patch.object(ai_agent, '_get_session_context', new=AsyncMock(return_value=[])):
            with patch.object(ai_agent, '_update_session_context', new=AsyncMock()):
                with patch.object(ai_agent, '_log_conversation', new=AsyncMock()):
                    response = await ai_agent.process_message(
                        user_id=123456789,
                        message="Hello",
                        session_id="test_session"
                    )

                    assert response.success is True
                    assert response.response == "Test response"
                    assert response.session_id == "test_session"


def test_create_user_endpoint(auth_headers):
    """Test user creation endpoint"""
    with patch('app.core.database.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post("/users", json={
            "telegram_user_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User"
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"