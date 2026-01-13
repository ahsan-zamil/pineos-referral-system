#!/bin/bash

# Quick start script for PineOS Referral System
# Run with: ./quickstart.sh

set -e

echo "🌲 PineOS Referral System - Quick Start"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker and try again."
  exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
  echo "❌ docker-compose not found. Please install docker-compose."
  exit 1
fi

echo "✓ docker-compose found"
echo ""

# Create .env file if it doesn't exist
if [ ! -f backend/.env ]; then
  echo "📝 Creating backend/.env from .env.example..."
  cp backend/.env.example backend/.env
  echo "✓ Created backend/.env"
else
  echo "✓ backend/.env already exists"
fi

echo ""
echo "🚀 Starting services with Docker Compose..."
echo ""

docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if backend is healthy
echo "Checking backend health..."
until curl -s http://localhost:8000/health > /dev/null; do
  echo "Waiting for backend..."
  sleep 2
done

echo "✓ Backend is ready"

echo ""
echo "✅ All services are running!"
echo ""
echo "📌 Service URLs:"
echo "   - Backend API:  http://localhost:8000"
echo "   - API Docs:     http://localhost:8000/docs"
echo "   - Frontend UI:  http://localhost:5173"
echo "   - PostgreSQL:   localhost:5432"
echo ""
echo "📚 Next steps:"
echo "   1. Visit http://localhost:5173 to see the UI"
echo "   2. Visit http://localhost:8000/docs for API documentation"
echo "   3. Run 'docker-compose logs -f' to view logs"
echo "   4. Run 'docker-compose down' to stop all services"
echo ""
echo "🧪 To run tests:"
echo "   cd backend && pytest -v"
echo ""
echo "Happy coding! 🎉"
