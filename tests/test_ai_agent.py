import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, User, Conversation, UserSession
from app.ai_agent import AIAgent
from app.config import settings

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_openai():
    with patch('openai.ChatCompletion.create') as mock:
        mock.return_value = Mock(
            choices=[Mock(message=Mock(content="Test AI response"))],
            usage=Mock(total_tokens=50)
        )
        yield mock


class TestAIAgent:

    def test_process_message_success(self, db_session, mock_openai):
        """Test successful message processing."""

        agent = AIAgent(db_session)
        result = agent.process_message(
            user_id=123,
            message="Hello, how are you?"
        )

        assert result["success"] is True
        assert result["response"] == "Test AI response"
        assert result["tokens_used"] == 50
        assert "session_id" in result

        # Verify conversation was saved
        conversations = db_session.query(Conversation).filter(
            Conversation.user_id == 123
        ).all()
        assert len(conversations) == 2  # User message + AI response

    def test_process_message_with_history(self, db_session, mock_openai):
        """Test message processing with conversation history."""

        agent = AIAgent(db_session)

        # First message
        result1 = agent.process_message(123, "First message")
        session_id = result1["session_id"]

        # Second message with same session
        result2 = agent.process_message(123, "Second message", session_id)

        assert result2["success"] is True
        assert result2["session_id"] == session_id

        # Verify OpenAI was called with history
        call_args = mock_openai.call_args[1]
        messages = call_args["messages"]
        assert len(messages) >= 3  # System + previous messages + new message

    def test_get_user_stats(self, db_session):
        """Test user statistics retrieval."""

        agent = AIAgent(db_session)

        # Create test data
        conv1 = Conversation(user_id=123, session_id="test", message_type="user",
                             content="Test", tokens_used=10)
        conv2 = Conversation(user_id=123, session_id="test", message_type="assistant",
                             content="Response", tokens_used=20)

        db_session.add_all([conv1, conv2])
        db_session.commit()

        stats = agent.get_user_stats(123)

        assert stats["total_messages"] == 2
        assert stats["total_tokens_used"] == 30

    def test_clear_user_history(self, db_session):
        """Test clearing user history."""

        agent = AIAgent(db_session)

        # Create test session
        session = UserSession(user_id=123, session_id="test", is_active=True)
        db_session.add(session)
        db_session.commit()

        result = agent.clear_user_history(123)

        assert result is True

        # Verify session is deactivated
        updated_session = db_session.query(UserSession).filter(
            UserSession.user_id == 123
        ).first()
        assert updated_session.is_active is False