#!/bin/bash
echo "Deploying Telegram AI Bot..."

# Build and deploy with Docker Compose
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check health
curl -f http://localhost:8000/health || {
    echo "Health check failed!"
    docker-compose logs telegram-bot
    exit 1
}

echo "Deployment successful!"
echo "Bot is running at http://localhost:8000"
echo "API documentation available at http://localhost:8000/docs"