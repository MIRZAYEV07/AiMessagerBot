import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app
from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override database dependency
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestAPI:

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Telegram AI Bot Backend"

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_process_message_success(self):
        """Test message processing API."""

        with patch('app.main.AIAgent') as mock_ai_agent:
            mock_ai_agent.return_value.process_message.return_value = {
                "response": "Test response",
                "session_id": "test-session",
                "tokens_used": 25,
                "success": True
            }

            response = client.post(
                "/api/message",
                json={
                    "user_id": 123,
                    "message": "Hello"
                },
                headers={"Authorization": "Bearer your-secret-api-key-here"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["response"] == "Test response"
            assert data["tokens_used"] == 25

    def test_process_message_unauthorized(self):
        """Test message processing without authorization."""

        response = client.post(
            "/api/message",
            json={
                "user_id": 123,
                "message": "Hello"
            }
        )

        assert response.status_code == 403  # No auth header

    def test_process_message_invalid_key(self):
        """Test message processing with invalid API key."""

        response = client.post(
            "/api/message",
            json={
                "user_id": 123,
                "message": "Hello"
            },
            headers={"Authorization": "Bearer invalid-key"}
        )

        assert response.status_code == 401

    def test_get_user_stats(self):
        """Test user statistics API."""

        with patch('app.main.AIAgent') as mock_ai_agent:
            mock_ai_agent.return_value.get_user_stats.return_value = {
                "total_messages": 10,
                "total_tokens_used": 500,
                "active_sessions": 1
            }

            response = client.get(
                "/api/stats/123",
                headers={"Authorization": "Bearer your-secret-api-key-here"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_messages"] == 10
            assert data["total_tokens_used"] == 500

    def test_clear_history(self):
        """Test clear history API."""

        with patch('app.main.AIAgent') as mock_ai_agent:
            mock_ai_agent.return_value.clear_user_history.return_value = True

            response = client.delete(
                "/api/history/123",
                headers={"Authorization": "Bearer your-secret-api-key-here"}
            )

            assert response.status_code == 200
            data = response.json()