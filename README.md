# Telegram AI Bot with Backend

A comprehensive Telegram bot integrated with an AI backend service, featuring conversation context management, user authentication, rate limiting, and comprehensive logging.

## Features

### 🤖 Telegram Bot
- Natural language conversation with AI
- Command handling (`/start`, `/help`, `/clear`, `/stats`)
- Inline keyboard interactions
- Rate limiting and access control
- User session management

### 🧠 AI Backend
- OpenAI GPT integration
- Conversation context memory
- Session-based chat history
- Async message processing
- Error handling and retries

### 🔧 Technical Features
- FastAPI backend with REST API
- SQLite database with conversation logging
- Docker containerization
- Comprehensive testing suite
- Rate limiting and security
- Health monitoring and statistics

## Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd telegram-ai-bot
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` file with your credentials:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
API_SECRET_KEY=your_secure_api_secret_key_here
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python -m app.main
```

## Docker Deployment

### Using Docker Compose
```bash
cd docker
docker-compose up -d
```

### Building Custom Image
```bash
docker build -f docker/Dockerfile -t telegram-ai-bot .
docker run -d --env-file .env -p 8000:8000 telegram-ai-bot
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `API_SECRET_KEY` | Backend API authentication key | Required |
| `DATABASE_URL` | Database connection string | `sqlite:///./telegram_bot.db` |
| `WHITELISTED_USERS` | Comma-separated user IDs | Empty (all users) |
| `ADMIN_USER_IDS` | Comma-separated admin user IDs | Empty |
| `RATE_LIMIT_MESSAGES` | Messages per rate limit window | 10 |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | 60 |

### Access Control
- Set `WHITELISTED_USERS` to restrict bot access to specific users
- Set `ADMIN_USER_IDS` for administrative commands
- Rate limiting prevents spam and abuse

## API Endpoints

### Authentication
All API endpoints require Bearer token authentication:
```
Authorization: Bearer YOUR_API_SECRET_KEY
```

### Endpoints
- `POST /chat` - Process chat messages
- `POST /users` - Create/update user information
- `POST /sessions/clear` - Clear user session
- `GET /health` - Health check
- `GET /stats` - Bot statistics

## Testing

### Run Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram      │    │   Bot Service   │    │  Backend API    │
│   Users         │───▶│   (Handlers)    │───▶│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                              ┌─────────────────┐
                                              │   AI Agent      │
                                              │   (OpenAI)      │
                                              └─────────────────┘
                                                       │
                                              ┌─────────────────┐
                                              │   Database      │
                                              │   (SQLite)      │
                                              └─────────────────┘
```

## Development

### Project Structure
```
app/
├── bot/          # Telegram bot handlers and middleware
├── backend/      # FastAPI backend and AI agent
├── core/         # Configuration, database, logging
└── main.py       # Application entry point
```

### Adding New Features
1. Add handlers in `app/bot/handlers.py`
2. Add API endpoints in `app/backend/api.py`
3. Update AI agent logic in `app/backend/ai_agent.py`
4. Add tests in `tests/`

## Monitoring and Logging

### Logs
- Application logs: `bot.log`
- Conversation logging in database
- Error tracking and debugging

### Health Monitoring
- Health check endpoint: `/health`
- Statistics endpoint: `/stats`
- Docker health checks included

## Security

### Best Practices Implemented
- API key authentication
- Rate limiting
- User access control
- Input validation
- Error handling without information leakage
- Secure token storage

## Troubleshooting

### Common Issues
1. **Bot not responding**: Check `TELEGRAM_BOT_TOKEN`
2. **AI not working**: Verify `OPENAI_API_KEY`
3. **Database errors**: Check file permissions
4. **Rate limiting**: Adjust `RATE_LIMIT_*` settings

### Debug Mode
Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.