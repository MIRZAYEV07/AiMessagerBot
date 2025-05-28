#!/bin/bash
echo "Running Telegram AI Bot Tests..."

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests with coverage
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

echo "Tests completed. Coverage report generated in htmlcov/"